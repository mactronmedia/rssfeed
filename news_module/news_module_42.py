import os
import re
import html
import json
import time
import aiohttp
import asyncio
import logging
import random
import feedparser
from datetime import datetime, UTC 
from selectolax.parser import HTMLParser
from typing import Optional, Dict, Any, List
from langdetect import detect, LangDetectException
from motor.motor_asyncio import AsyncIOMotorClient
from utilities.helpers import proxy, retry

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TYPE = 'news'

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/?maxPoolSize=10')

USER_AGENTS = [ua.strip() for ua in os.getenv('USER_AGENTS', '').split(',') if ua.strip()] or [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

 
def get_random_headers() -> dict:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/xml,application/rss+xml",
        "Connection": "keep-alive",
        "Accept-Language": "en-US,en;q=0.5",
    }
    return headers


# Database class with all database operations
class Database:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['news']
    feeds = db['feeds']
    articles = db['articles']
    feed_stats = db['feed_stats']  # Add this new collection

    @staticmethod
    async def feed_exists(url: str) -> bool:
        return await Database.feeds.find_one({'feed_url': url}) is not None

    @staticmethod
    async def article_exists(links: List[str]) -> List[str]:
        """Check if articles exist in bulk."""
        existing = await Database.articles.find({"link": {"$in": links}}).to_list(length=None)
        existing_links = {doc['link'] for doc in existing}
        return existing_links

    @staticmethod
    async def insert_articles(docs: List[Dict[str, Any]]) -> List[Any]:
        if docs:
            res = await Database.articles.insert_many(docs)
            logging.info(f"Inserted {len(res.inserted_ids)} articles.")
            return res.inserted_ids
        return []

    @staticmethod
    async def update_feed_last_checked(feed_id: Any, last_checked: datetime) -> None:
        await Database.feeds.update_one(
            {'_id': feed_id}, 
            {'$set': {'last_checked': last_checked}}
        )

    @staticmethod
    async def update_feed_language(feed_id: Any, language: str) -> None:
        await Database.feeds.update_one(
            {'_id': feed_id}, 
            {'$set': {'language': language}}
        )

    @staticmethod
    async def update_feed_last_updated(feed_id: Any, last_updated: datetime) -> None:
        await Database.feeds.update_one(
            {'_id': feed_id}, 
            {'$set': {'last_updated': last_updated}}
        )

    @staticmethod
    async def get_feed_by_url(url: str) -> Optional[Dict[str, Any]]:
        return await Database.feeds.find_one({'feed': url})

    @staticmethod
    async def create_feed(feed_data: Dict[str, Any]) -> Any:
        result = await Database.feeds.insert_one(feed_data)
        logging.info(f"New feed inserted: {feed_data.get('title')} ({feed_data.get('feed')})")
        return result.inserted_id

    @staticmethod
    async def update_feed_stats(feed_id: Any, articles_added: int) -> None:
        """Update or create feed statistics."""
        await Database.feed_stats.update_one(
            {'feed_id': feed_id},
            {'$inc': {'total_items': articles_added}, '$set': {'last_updated': datetime.now(UTC)}},
            upsert=True
        )

# RSS Parser
class RSSParser:
    @staticmethod
    def detect_language(text: str) -> str:
        try:
            return detect(text)
        except LangDetectException:
            return "unknown"

    @staticmethod
    @retry(retries=3, delay=1, backoff=2, jitter=True)
    @proxy 
    async def fetch_feed(url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        try:
            async with session.get(url, headers=get_random_headers()) as response:
                if response.status != 200:
                    return {"error": f"HTTP {response.status}"}
                data = feedparser.parse(await response.text())

                if data.bozo:
                    return {"error": str(data.bozo_exception)}
                                
                return {"feed": data.feed, "entries": data.entries}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def process_feed(url: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore):
        async with semaphore: 
            result = await RSSParser.fetch_feed(url, session)
            if "error" in result:
                logging.error(f"Feed error {url}: {result['error']}")
                return

            feed_data = result["feed"]
            entries = result["entries"]

            first_article_language = RSSParser.detect_language(entries[0].get('description', ''))

            feed_id = await RSSParser.get_or_create_feed(url, feed_data, first_article_language)
            
            if feed_id:
                new_articles_added = await RSSParser.process_articles(entries, feed_id, session)

                if new_articles_added:
                    await Database.update_feed_last_updated(feed_id, datetime.now(UTC))
                    await Database.update_feed_stats(feed_id, new_articles_added) 

    @staticmethod
    async def get_or_create_feed(url: str, feed_data: dict, feed_language: str):
        existing = await Database.get_feed_by_url(url)
        now = datetime.now(UTC)        
        if existing:
            logging.info(f"Feed {url} already exists. Skipping feed save.")
            
            await Database.update_feed_last_checked(existing['_id'], now)
            if existing.get('language') != feed_language:
                await Database.update_feed_language(existing['_id'], feed_language)

            return existing.get('_id')
       
        # Create new feed
        new_feed = {
            'title': feed_data.get('title', 'Untitled'),
            'description': feed_data.get('description', ''),
            'language': feed_language,
            'last_updated': now,
            'last_checked': now,
            'link': feed_data.get('link', ''),
            'feed': url,
            'image': RSSParser.parse_image(feed_data),
        }
        
        return await Database.create_feed(new_feed)

    @staticmethod
    def parse_image(info: dict) -> str:
        image = getattr(info, 'image', None)
        if isinstance(image, str):
            return image
        elif hasattr(image, 'href'):
            return image.href
        elif isinstance(image, dict):
            return image.get('url', '')
        return ''

    @staticmethod
    async def process_articles(entries: List[dict], feed_id, session: aiohttp.ClientSession) -> bool:
        articles = []
        no_thumbnail = []

        all_links = [entry.get('link') for entry in entries if entry.get('link')]
        existing_links = await Database.article_exists(all_links)  # Bulk check if articles exist

        for entry in entries:
            link = entry.get('link')
            if not link or link in existing_links:
                continue
            try:
                article = await RSSParser.process_entry(entry, feed_id, no_thumbnail)
                if article:
                    articles.append(article)
            except Exception as e:
                logging.error(f"Error processing entry from {entry.get('link', 'unknown')}: {e}")

        if no_thumbnail:
            ogs = await RSSParser.fetch_og_images(no_thumbnail, session)
            for article in articles:
                if not article['thumbnail']:
                    article['thumbnail'] = ogs.get(article['link'])

        inserted_ids = await Database.insert_articles(articles)
        return len(inserted_ids) if inserted_ids else 0  # Return the count

    @staticmethod
    async def process_entry(entry: dict, feed_id: int, no_thumbnail: List[str]) -> dict | None:
        link = entry.get('link')
        if not link:
            return None
            
        description = entry.get('description', '')
        
        published_parsed = entry.get("published_parsed")
        published = datetime(*published_parsed[:6]) if published_parsed else datetime.now(UTC)
        
        article_language = RSSParser.detect_language(description)

        thumbnail = RSSParser.extract_thumbnail(entry)
        if not thumbnail:
            thumbnail = RSSParser.extract_image_from_description(description)
            if not thumbnail:
                no_thumbnail.append(link)

        return {
            'feed_id': feed_id,
            'title': entry.get('title', ''),
            'description': RSSParser.clean_html(description),
            'content': '',
            'summarize': '',
            'type': TYPE,
            'language': article_language,
            'published': published,
            'link': link,
            'thumbnail': thumbnail,
        }

    @staticmethod
    def clean_html(html_text: str) -> str:
        text = re.sub(r'</?p[^>]*>', '\n', html_text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&(#?\w+);', lambda m: html.unescape(m.group(0)), text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def extract_thumbnail(entry: dict) -> str:
        # Try media_thumbnail
        if "media_thumbnail" in entry and entry["media_thumbnail"]:
            return entry["media_thumbnail"][0].get("url", "")

        # Try media_content
        if "media_content" in entry:
            for media in entry["media_content"]:
                if "url" in media:
                    return media["url"]

        # Try enclosure
        if "enclosures" in entry:
            for enclosure in entry["enclosures"]:
                if enclosure.get("type", "").startswith("image/"):
                    return enclosure.get("href", "")

        # Try extracting image from content:encoded
        content = entry.get("content", [{}])[0].get("value", "")
        img_match = re.search(r'<img[^>]+src="([^"]+)"', content)
        if img_match:
            return img_match.group(1)

        return ""

    @staticmethod
    def extract_image_from_description(description: str) -> str:
        """Extract image URL from HTML description content."""
        if not description:
            return ""
        
        img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', description, re.IGNORECASE)
        if img_matches:
            return img_matches[0]
        
        srcset_matches = re.findall(r'srcset=["\']([^"\']+)["\']', description, re.IGNORECASE)
        if srcset_matches:
            urls = re.split(r',\s*', srcset_matches[0])
            if urls:
                return urls[0].split()[0] 
        
        return ""
        
    @staticmethod
    async def fetch_og_images(urls: List[str], session: aiohttp.ClientSession) -> Dict[str, Optional[str]]:
        results = await asyncio.gather(*(RSSParser.get_og(u, session) for u in urls))
        return dict(results)

    @staticmethod
    async def get_og(url: str, session: aiohttp.ClientSession) -> tuple[str, Optional[str]]:
        try:
            logging.info(f'Fetching OG image for {url}')
            async with session.get(url, headers=get_random_headers(), timeout=10) as response:
                if response.status != 200:
                    return url, None

                html = await response.text()
                tree = HTMLParser(html)
                meta_tag = tree.css_first('meta[property="og:image"]')
                return url, meta_tag.attributes.get('content') if meta_tag else None

        except Exception:
            return url, None

# Entry point
async def main():
    start_time = time.time()

    rss_urls = [
        'https://www.arabnews.com/rss.xml',
        'https://medium.com/feed/tomtalkspython',
        'https://www.gsmarena.com/rss-news-reviews.php3',
        'https://www.intelligentcio.com/feed/',
        'https://www.gamespress.com/News/RSS',
        'https://qz.com/rss',
        'https://www.independent.co.uk/rss',
        'https://feeds.bbci.co.uk/news/rss.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
        'https://www.aljazeera.com/xml/rss/all.xml',
        'https://feeds.skynews.com/feeds/rss/home.xml',
        'https://abcnews.go.com/abcnews/usheadlines',
        'https://www.cbsnews.com/latest/rss/main',
        'https://feeds.content.dowjones.io/public/rss/RSSOpinion',
        'https://feeds.nbcnews.com/nbcnews/public/world',
        'https://www.newyorker.com/feed/news',
        'https://www.theguardian.com/us-news/rss',
        'https://www.latimes.com/world/rss2.0.xml',
        'https://www.yorkshireeveningpost.co.uk/rss',
        'https://orthodoxtimes.com/feed/',
        'https://mashable.com/feeds/rss/all',
        'https://indianexpress.com/feed/',
        'https://www.theverge.com/rss/index.xml',
        'https://arstechnica.com/feed/',
        'https://www.engadget.com/rss.xml',
        'https://www.wired.com/feed',
        'https://www.deutschland.de/en/feed',
        'https://www.spiegel.de/index.rss',
        'https://img.rtvslo.si/feeds/00.xml',
        'https://www.france24.com/fr/rss',
        'https://www.france24.com/es/rss'
    ]
    
    semaphore = asyncio.Semaphore(5)  # Limit concurrency to 5 requests at a time

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(RSSParser.process_feed(url, session, semaphore) for url in rss_urls))

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total execution time: {elapsed_time:.2f} seconds")  # Print the total time

if __name__ == '__main__':
    asyncio.run(main())