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
from bson import ObjectId
from datetime import datetime, UTC 
from selectolax.parser import HTMLParser
from typing import Optional, Dict, Any, List
from langdetect import detect, LangDetectException
from motor.motor_asyncio import AsyncIOMotorClient
from utilities.helpers import proxy, retry

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/?maxPoolSize=10')

USER_AGENTS = [ua.strip() for ua in os.getenv('USER_AGENTS', '').split(',') if ua.strip()] or [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_random_headers() -> dict:
    return {"User-Agent": random.choice(USER_AGENTS)}

class Database:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['news']
    feeds = db['feeds']
    articles = db['articles']
    
    # Cache for existing article links
    _existing_links_cache = set()
    _cache_loaded = False

    @classmethod
    async def initialize_cache(cls):
        """Preload existing article links into memory"""
        if not cls._cache_loaded:
            cls._existing_links_cache = {doc['link'] async for doc in cls.articles.find({}, {'link': 1})}
            cls._cache_loaded = True
            logging.info(f"Preloaded {len(cls._existing_links_cache)} existing article links")

    @classmethod
    async def get_all_feeds(cls) -> List[Dict[str, Any]]:
        """Retrieve all feeds with only necessary fields"""
        return await cls.feeds.find(
            {},
            {'feed_url': 1, '_id': 1, 'last_updated': 1}
        ).to_list(length=None)

    @classmethod
    async def bulk_insert_articles(cls, docs: List[Dict]) -> int:
        """Bulk insert articles with optimized write concern"""
        if not docs:
            return 0
        try:
            result = await cls.articles.insert_many(docs, ordered=False)
            # Update cache with new links
            cls._existing_links_cache.update(doc['link'] for doc in docs)
            logging.info(f"Inserted {len(result.inserted_ids)} articles")
            return len(result.inserted_ids)
        except Exception as e:
            logging.error(f"Bulk insert error (duplicates may exist): {str(e)}")
            return 0

    @classmethod
    async def bulk_update_feeds(cls, updates: List[Dict]):
        """Bulk update feed timestamps with correct operation format"""
        if not updates:
            return
        
        # Validate updates before processing
        valid_updates = []
        for update in updates:
            if not isinstance(update.get('_id'), ObjectId):
                logging.error(f"Invalid _id in update: {update.get('_id')}")
                continue
            if not isinstance(update.get('data'), dict):
                logging.error(f"Invalid data in update: {update.get('data')}")
                continue
            valid_updates.append(update)
        
        if not valid_updates:
            return

        bulk_ops = []
        for update in valid_updates:
            bulk_ops.append({
                'updateOne': {  # Note: MongoDB uses camelCase for operation names
                    'filter': {'_id': update['_id']},
                    'update': {'$set': update['data']}
                }
            })
        
        try:
            result = await cls.feeds.bulk_write(bulk_ops)
            logging.info(f"Updated {result.modified_count} feed timestamps")
        except Exception as e:
            logging.error(f"Bulk update error: {str(e)}")
            # Log the first few operations for debugging
            for op in bulk_ops[:3]:
                logging.debug(f"Example operation: {op}")
            
class RSSProcessor:
    def __init__(self):
        self.session = None
        self.semaphore = asyncio.Semaphore(5)
        self.feed_updates = []
        self.new_articles = []

    async def process_all_feeds(self):
        """Main processing pipeline"""
        await Database.initialize_cache()
        
        feeds = await Database.get_all_feeds()
        if not feeds:
            logging.warning("No feeds found in database")
            return

        logging.info(f"Processing {len(feeds)} feeds")
        
        async with aiohttp.ClientSession() as self.session:
            await asyncio.gather(*[
                self.process_feed(feed) for feed in feeds
            ])
        
        # Bulk operations at the end
        if self.new_articles:
            await Database.bulk_insert_articles(self.new_articles)
        if self.feed_updates:
            await Database.bulk_update_feeds(self.feed_updates)

    async def process_feed(self, feed: Dict):
        """Process a single feed"""
        async with self.semaphore:
            try:
                feed_url = feed['feed_url']
                logging.info(f"Processing feed: {feed_url}")
                
                # Fetch and parse feed
                entries = await self.fetch_feed(feed_url)
                if not entries:
                    self.feed_updates.append({
                        '_id': feed['_id'],
                        'data': {'last_checked': datetime.now(UTC)}
                    })
                    return

                # Process entries
                new_count = await self.process_entries(entries, feed['_id'])
                if new_count:
                    self.feed_updates.append({
                        '_id': feed['_id'],
                        'data': {
                            'last_updated': datetime.now(UTC),
                            'last_checked': datetime.now(UTC)
                        }
                    })
                else:
                    self.feed_updates.append({
                        '_id': feed['_id'],
                        'data': {'last_checked': datetime.now(UTC)}
                    })

            except Exception as e:
                logging.error(f"Error processing feed {feed_url}: {str(e)}")

    async def fetch_feed(self, url: str) -> List[Dict]:
        """Fetch and parse RSS feed"""
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"HTTP {response.status} for {url}")
                    return []
                data = feedparser.parse(await response.text())
                return data.entries if hasattr(data, 'entries') else []
        except Exception as e:
            logging.error(f"Fetch error for {url}: {str(e)}")
            return []

    async def process_entries(self, entries: List[Dict], feed_id: str) -> int:
        """Process feed entries and collect new articles"""
        new_count = 0
        for entry in entries:
            if not entry.get('link'):
                continue
                
            if entry['link'] in Database._existing_links_cache:
                continue
                
            try:
                article = self.create_article(entry, feed_id)
                if article:
                    self.new_articles.append(article)
                    Database._existing_links_cache.add(entry['link'])
                    new_count += 1
            except Exception as e:
                logging.error(f"Error processing entry: {str(e)}")
        
        return new_count

    def create_article(self, entry: Dict, feed_id: str) -> Dict:
        """Create article document from entry"""
        return {
            'feed_id': feed_id,
            'title': entry.get('title', ''),
            'description': self.clean_html(entry.get('description', '')),
            'link': entry['link'],
            'published': self.parse_date(entry),
            'thumbnail': self.extract_thumbnail(entry),
            'language': self.detect_language(entry.get('description', ''))
        }

    @staticmethod
    def clean_html(text: str) -> str:
        """Basic HTML cleaning"""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return html.unescape(text)

    @staticmethod
    def parse_date(entry: Dict) -> datetime:
        """Parse entry published date"""
        if 'published_parsed' in entry:
            return datetime(*entry.published_parsed[:6])
        return datetime.now(UTC)

    @staticmethod
    def extract_thumbnail(entry: Dict) -> str:
        """Extract thumbnail from entry"""
        # (Keep your existing thumbnail extraction logic)
        return ""

    @staticmethod
    def detect_language(text: str) -> str:
        """Detect language with fallback"""
        try:
            return detect(text) if text else 'unknown'
        except:
            return 'unknown'

async def main():
    start = time.time()
    processor = RSSProcessor()
    await processor.process_all_feeds()
    logging.info(f"Completed in {time.time() - start:.2f} seconds")

if __name__ == '__main__':
    asyncio.run(main())