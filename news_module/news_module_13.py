import os
import re
import json
import aiohttp
import asyncio
import logging
import random
import feedparser
import urllib.parse
import hashlib
from datetime import datetime
from aiohttp import ClientSession
from typing import Optional, Dict, Any, List, Tuple
from utilities.helpers import proxy, retry
from motor.motor_asyncio import AsyncIOMotorClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from environment variables (default values provided)
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')

USER_AGENTS = [ua for ua in os.getenv('USER_AGENTS', "").split(",") if ua.strip()] or [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Global headers with a random user-agent
headers = {"User-Agent": random.choice(USER_AGENTS)}

class Database:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['news']
    collection_feeds = db['feeds']
    collection_articles = db['articles']

    @staticmethod
    async def feed_exists(feed_url: str) -> bool:
        doc = await Database.collection_feeds.find_one({'feed_url': feed_url})
        return doc is not None

    @staticmethod
    async def article_exists(link: str) -> bool:
        doc = await Database.collection_articles.find_one({'link': link})
        return doc is not None

    @staticmethod
    async def bulk_insert_articles(article_data_list: list) -> list:
        if article_data_list:
            result = await Database.collection_articles.insert_many(article_data_list)
            logging.info(f"Inserted {len(result.inserted_ids)} articles.")
            return result.inserted_ids
        return []

    @staticmethod
    async def update_article_thumbnail(link: str, thumbnail_url: str) -> None:
        await Database.collection_articles.update_one(
            {'link': link},
            {'$set': {'thumbnail': thumbnail_url}}
        )

class RSSParser:
    @staticmethod
    @proxy
    @retry(retries=3, delay=1, backoff=2, jitter=True)
    async def parse_feed(feed_url: str, session: ClientSession) -> Dict[str, Any]:
        """Parse an RSS feed and return structured data."""
        try:
            async with session.get(feed_url) as response:
                if response.status != 200:
                    return {"error": f"Failed to fetch RSS feed. Status: {response.status}"}
                
                feed_content = await response.text()
                parsed_feed = feedparser.parse(feed_content)
                
                if parsed_feed.bozo:
                    return {"error": f"RSS parse error: {parsed_feed.bozo_exception}"}
                
                return {
                    "feed": parsed_feed.feed,
                    "entries": parsed_feed.entries,
                    "status": "success"
                }
        except Exception as e:
            logging.error(f"Error parsing feed: {e}")
            return {"error": str(e)}

    @staticmethod
    async def process_feed(feed_url: str, session: ClientSession):
        """Process an RSS feed and store its contents."""
        feed_data = await RSSParser.parse_feed(feed_url, session)
        
        if "error" in feed_data:
            logging.error(f"Failed to process feed {feed_url}: {feed_data['error']}")
            return
        
        feed_object_id = await RSSParser.get_or_create_feed(feed_url, feed_data['feed'])
        
        if feed_object_id:
            await RSSParser.process_articles(feed_data['entries'], feed_object_id, session)
        else:
            logging.error(f"Failed to get or create feed for {feed_url}")

    @staticmethod
    async def get_or_create_feed(feed_url: str, feed_info: Dict[str, Any]):
        if await Database.feed_exists(feed_url):
            logging.info(f"Feed {feed_url} already exists. Skipping feed save.")
            existing_feed = await Database.collection_feeds.find_one({'feed_url': feed_url})
            return existing_feed['_id'] if existing_feed else None
        else:
            return await RSSParser.create_new_feed(feed_url, feed_info)

    @staticmethod
    async def create_new_feed(feed_url: str, feed_info: Dict[str, Any]):
        feed_data = {
            'feed_url': feed_url,
            'title': feed_info.get('title', 'Untitled Feed'),
            'description': feed_info.get('description', ''),
            'link': feed_info.get('link', ''),
            'language': feed_info.get('language', 'en'),
            'published': feed_info.get('published', ''),
            'image': RSSParser.parse_feed_image(feed_info),
            'last_updated': datetime.utcnow()
        }

        result = await Database.collection_feeds.insert_one(feed_data)
        logging.info(f"Inserted feed with id: {result.inserted_id}")
        return result.inserted_id

    @staticmethod
    def parse_feed_image(feed_info: Dict[str, Any]) -> str:
        """Parse feed image from different possible formats and return URL only."""
        if not hasattr(feed_info, 'image'):
            return ''
            
        image = feed_info.image
        if isinstance(image, str):
            return image
        elif hasattr(image, 'href'):
            return image.href
        elif isinstance(image, dict):
            return image.get('url', '')
        return ''

    @staticmethod
    async def process_articles(entries: list, feed_object_id: str, session: ClientSession):
        tasks = []
        
        for entry in entries:
            tasks.append(RSSParser.process_article_entry(entry, feed_object_id, session))

        results = await asyncio.gather(*tasks)
        article_data_list = [res for res in results if res]

        if article_data_list:
            inserted_ids = await Database.bulk_insert_articles(article_data_list)
            # Process thumbnails for new articles
            await RSSParser.process_article_thumbnails(article_data_list, session)

    @staticmethod
    async def process_article_thumbnails(articles: List[Dict], session: ClientSession):
        """Process and validate the thumbnail for each article."""
        for article in articles:
            if not article.get('thumbnail'):
                continue
                
            if await RSSParser.validate_image_url(article['thumbnail'], session):
                await Database.update_article_thumbnail(article['link'], article['thumbnail'])
            else:
                # If primary thumbnail is invalid, try to find a valid one from content
                content = article.get('content', '')
                if content:
                    images = RSSParser.extract_images_from_html(content)
                    for img in images:
                        if await RSSParser.validate_image_url(img, session):
                            await Database.update_article_thumbnail(article['link'], img)
                            break

    @staticmethod
    async def validate_image_url(url: str, session: ClientSession) -> bool:
        """Check if an image URL is accessible and valid."""
        if not url:
            return False
            
        try:
            async with session.head(url, allow_redirects=True) as response:
                content_type = response.headers.get('Content-Type', '').lower()
                return response.status == 200 and content_type.startswith('image/')
        except Exception:
            return False

    @staticmethod
    async def get_og_image(url: str, session: ClientSession) -> Optional[str]:
        """Extract og:image from webpage meta tags."""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                og_image_pattern = re.compile(r'<meta[^>]+property="og:image"[^>]+content="([^">]+)"', re.IGNORECASE)
                match = og_image_pattern.search(html)
                return match.group(1) if match else None
        except Exception as e:
            logging.warning(f"Error fetching og:image for {url}: {e}")
            return None

    @staticmethod
    async def process_article_entry(entry: Dict[str, Any], feed_object_id: str, 
                                  session: ClientSession) -> Optional[Dict[str, Any]]:
        """Process an individual article entry from the RSS feed."""
        link = entry.get('link', '')
        if not link:
            return None
            
        if await Database.article_exists(link):
            logging.info(f"Article with link {link} already exists. Skipping.")
            return None

        # Extract the primary thumbnail
        thumbnail = RSSParser.extract_thumbnail(entry)
        
        # If no thumbnail found in RSS, try to get og:image
        if not thumbnail:
            thumbnail = await RSSParser.get_og_image(link, session)

        # Parse and normalize the publication date
        published_date = RSSParser.parse_publication_date(entry)

        return {
            'feed_id': feed_object_id,
            'title': entry.get('title', 'No Title'),
            'description': entry.get('description', ''),
            'link': link,
            'published': published_date,
            'categories': RSSParser.extract_categories(entry),
            'thumbnail': thumbnail,
            'last_updated': datetime.utcnow()
        }
        
    @staticmethod
    def extract_thumbnail(entry: Dict[str, Any]) -> str:
        """Extract thumbnail URL from entry using priority order."""
        # Priority 1: Explicit media thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url', '')
        
        # Priority 2: Image field
        if hasattr(entry, 'image') and entry.image:
            if isinstance(entry.image, str):
                return entry.image
            elif hasattr(entry.image, 'href'):
                return entry.image.href
            elif isinstance(entry.image, dict):
                return entry.image.get('url', '')
        
        # Priority 3: Media content images
        if hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if media.get('medium') == 'image' or media.get('type', '').startswith('image/'):
                    return media.get('url', '')
                            
        return ''

    @staticmethod
    def extract_images_from_html(html_content: str) -> List[str]:
        """Extract image URLs from HTML content."""
        if not html_content:
            return []
            
        # Simple regex to find img tags
        img_pattern = re.compile(r'<img[^>]+src="([^">]+)"', re.IGNORECASE)
        return img_pattern.findall(html_content)

    @staticmethod
    def extract_categories(entry: Dict[str, Any]) -> List[str]:
        """Extract categories/tags from entry."""
        if not hasattr(entry, 'tags'):
            return []
            
        return [tag.term if hasattr(tag, 'term') else tag for tag in entry.tags]

    @staticmethod
    def parse_publication_date(entry: Dict[str, Any]) -> str:
        """Parse and normalize publication date."""
        date_fields = ['published', 'updated', 'pubDate', 'dc_date']
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                return getattr(entry, field)
        return 'N/A'

async def main():
 
    rss_urls = [

        'https://www.aljazeera.com/xml/rss/all.xml',  # !
        'https://www.cbsnews.com/latest/rss/main', # !
        'https://www.theguardian.com/us-news/rss', # !
        'https://mashable.com/feeds/rss/all', # !
        'https://www.theverge.com/rss/index.xml', # !
        'https://img.rtvslo.si/feeds/00.xml'
        
    ]

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [RSSParser.process_feed(url, session) for url in rss_urls]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

    # BASIC!