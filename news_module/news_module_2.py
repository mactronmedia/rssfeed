import os
import re
import json
import aiohttp
import asyncio
import logging
import random
import feedparser
import urllib.parse
from aiohttp import ClientSession
from typing import Optional, Dict, Any
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
    async def article_exists(article_id: str) -> bool:
        doc = await Database.collection_articles.find_one({'article_id': article_id})
        return doc is not None

    @staticmethod
    async def bulk_insert_articles(article_data_list: list) -> list:
        if article_data_list:
            result = await Database.collection_articles.insert_many(article_data_list)
            logging.info(f"Inserted {len(result.inserted_ids)} articles.")
            return result.inserted_ids
        return []

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
            await RSSParser.process_articles(feed_data['entries'], feed_object_id)
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
            'image': feed_info.get('image', {}).get('href', '') if hasattr(feed_info, 'image') else ''
        }

        result = await Database.collection_feeds.insert_one(feed_data)
        logging.info(f"Inserted feed with id: {result.inserted_id}")
        return result.inserted_id

    @staticmethod
    async def process_articles(entries: list, feed_object_id: str):
        tasks = []
        
        for entry in entries:
            tasks.append(RSSParser.process_article_entry(entry, feed_object_id))

        results = await asyncio.gather(*tasks)
        article_data_list = [res for res in results if res]

        if article_data_list:
            await Database.bulk_insert_articles(article_data_list)

    @staticmethod
    async def process_article_entry(entry: Dict[str, Any], feed_object_id: str) -> Optional[Dict[str, Any]]:
        """Process an individual article entry from the RSS feed."""
        # Generate a unique ID for the article
        article_id = RSSParser.generate_article_id(entry)
        
        if await Database.article_exists(article_id):
            logging.info(f"Article {article_id} already exists. Skipping.")
            return None

        # Extract media content (images, videos, etc.)
        media_content = []
        if hasattr(entry, 'media_content'):
            for media in entry.media_content:
                media_content.append({
                    'url': media.get('url'),
                    'type': media.get('type'),
                    'medium': media.get('medium'),
                    'width': media.get('width'),
                    'height': media.get('height')
                })

        # Extract enclosures (podcasts, etc.)
        enclosures = []
        if hasattr(entry, 'enclosures'):
            for enc in entry.enclosures:
                enclosures.append({
                    'url': enc.get('href'),
                    'type': enc.get('type'),
                    'length': enc.get('length')
                })

        return {
            'feed_id': feed_object_id,
            'article_id': article_id,
            'title': entry.get('title', 'No Title'),
            'description': entry.get('description', ''),
            'content': entry.get('content', [{}])[0].get('value') if hasattr(entry, 'content') else '',
            'link': entry.get('link', ''),
            'published': entry.get('published', entry.get('updated', 'N/A')),
            'author': entry.get('author', ''),
            'categories': [tag.term if hasattr(tag, 'term') else tag for tag in entry.get('tags', [])],
            'media_content': media_content,
            'enclosures': enclosures,
            'thumbnail': (
                entry.get('media_thumbnail', [{}])[0].get('url') if hasattr(entry, 'media_thumbnail') else
                entry.get('image', {}).get('href') if hasattr(entry, 'image') else ''
            )
        }

    @staticmethod
    def generate_article_id(entry: Dict[str, Any]) -> str:
        """Generate a unique ID for the article based on its content."""
        if entry.get('id'):
            return entry.id.split('/')[-1]  # Use the last part of the URL as ID
        elif entry.get('link'):
            return hashlib.md5(entry.link.encode()).hexdigest()
        else:
            # Fallback: hash the title and published date
            unique_str = f"{entry.get('title', '')}-{entry.get('published', '')}"
            return hashlib.md5(unique_str.encode()).hexdigest()

async def main():
    # Example usage with NY Times World RSS feed
    rss_url = "https://feeds.bbci.co.uk/news/rss.xml"
    
    async with aiohttp.ClientSession(headers=headers) as session:
        await RSSParser.process_feed(rss_url, session)

if __name__ == "__main__":
    asyncio.run(main())