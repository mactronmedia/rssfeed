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
from utilities.helpers import setup_logging, proxy, retry


# --------------------------
# Configuration and Constants
# --------------------------
setup_logging()  #
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TYPE = 'news'

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/?maxPoolSize=10')

USER_AGENTS = [ua.strip() for ua in os.getenv('USER_AGENTS', '').split(',') if ua.strip()] or [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# --------------------------
# HTTP Utilities
# --------------------------

def get_random_headers() -> dict:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/xml,application/rss+xml",
        "Connection": "keep-alive",
        "Accept-Language": "en-US,en;q=0.5",
    }
    return headers

# --------------------------
# Database Operations
# --------------------------

class Database:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['news']
    feeds = db['feeds']
    articles = db['articles']
    feed_stats = db['feed_stats']  # Add this new collection

    @staticmethod
    async def get_all_feeds() -> List[Dict[str, Any]]:
        """Get all feeds from the database."""
        return await Database.feeds.find({}).to_list(length=None)

    @staticmethod
    async def article_exists(links: List[str]) -> List[str]:
        """Check if news exist in bulk."""
        existing = await Database.articles.find({"link": {"$in": links}}).to_list(length=None)
        existing_links = {doc['link'] for doc in existing}
        return existing_links

    @staticmethod
    async def insert_news(docs: List[Dict[str, Any]]) -> List[Any]:
        if docs:
            res = await Database.articles.insert_many(docs)
            logging.info(f"Inserted {len(res.inserted_ids)} news.")
            return res.inserted_ids
        return []

    @staticmethod
    async def update_feed_last_checked(feed_id: Any, last_checked: datetime) -> None:
        await Database.feeds.update_one(
            {'_id': feed_id}, 
            {'$set': {'last_checked': last_checked}}
        )

    @staticmethod
    async def update_feed_last_updated(feed_id: Any, last_updated: datetime) -> None:
        await Database.feeds.update_one(
            {'_id': feed_id}, 
            {'$set': {'last_updated': last_updated}}
        )

    @staticmethod
    async def update_feed_stats(feed_id: Any, news_added: int) -> None:
        """Update or create feed statistics."""
        await Database.feed_stats.update_one(
            {'feed_id': feed_id},
            {'$inc': {'total_items': news_added}, '$set': {'last_updated': datetime.now(UTC)}},
            upsert=True
        )

# --------------------------
# RSS Parser
# --------------------------

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
    async def process_feed(feed: Dict[str, Any], session: aiohttp.ClientSession, semaphore: asyncio.Semaphore):
        async with semaphore:
            url = feed['feed']

            result = await RSSParser.fetch_feed(url, session)
            if "error" in result:
                logging.error(f"Feed error {url}: {result['error']}")
                return

            entries = result["entries"]
            if not entries:
                logging.warning(f"No entries found in feed: {url}")
                return

            feed_id = feed['_id']
            new_news_added = await RSSParser.process_articles(entries, feed_id, feed['language'], session)
            
            if new_news_added:
                await Database.update_feed_last_updated(feed_id, datetime.now(UTC))
                await Database.update_feed_stats(feed_id, new_news_added)
            
            await Database.update_feed_last_checked(feed_id, datetime.now(UTC))
        
    @staticmethod
    async def process_articles(entries: List[dict], feed_id: str, feed_language: str, session: aiohttp.ClientSession) -> bool:
        all_links = [entry.get('link') for entry in entries if entry.get('link')]
        existing_links = await Database.article_exists(all_links)
        news, no_thumbnail = await RSSParser.process_entries(entries, feed_id, feed_language, existing_links)
        
        await RSSParser.process_thumbnails(news, no_thumbnail, session)
        inserted_ids = await Database.insert_news(news)
        return len(inserted_ids) if inserted_ids else 0

    @staticmethod
    async def process_entries(entries: List[dict], feed_id: str, feed_language: str, existing_links: List[str]) -> tuple[List[dict], List[str]]:
        news = []
        no_thumbnail = []

        for entry in entries:
            if not await RSSParser.is_valid_entry(entry, existing_links):
                continue
            try:
                article = await RSSParser.process_entry(entry, feed_id, feed_language, no_thumbnail)
                if article:
                    news.append(article)
            except Exception as e:
                logging.error(f"Error processing entry from {entry.get('link', 'unknown')}: {e}")
        
        return news, no_thumbnail

    @staticmethod
    async def is_valid_entry(entry: dict, existing_links: List[str]) -> bool:
        link = entry.get('link')
        if not link or link in existing_links:
            return False
        return True

    @staticmethod
    async def process_entry(entry: dict, feed_id: int, feed_language: str, no_thumbnail: List[str]) -> Optional[dict]:
        link = entry.get('link')
        if not link:
            return None
            
        description = entry.get('description', '')
        published = RSSParser.get_published_date(entry)
        
        # Try to detect language from description, fall back to feed language
        try:
            article_language = RSSParser.detect_language(description) if description else feed_language
        except:
            article_language = feed_language
            
        thumbnail = RSSParser.get_thumbnail(entry, description, no_thumbnail)

        return {
            'feed_id': feed_id,
            'title': entry.get('title', ''),
            'description': RSSParser.clean_html(description),
            'content': '',
            'summarize': '',
            'language': article_language,
            'published': published,
            'link': link,
            'thumbnail': thumbnail,
        }

    @staticmethod
    def get_published_date(entry: dict) -> datetime:
        published_parsed = entry.get("published_parsed")
        return datetime(*published_parsed[:6]) if published_parsed else datetime.now(UTC)

    @staticmethod
    async def process_thumbnails(news: List[dict], no_thumbnail: List[str], session: aiohttp.ClientSession) -> None:
        if no_thumbnail:
            ogs = await RSSParser.fetch_og_images(no_thumbnail, session)
            for article in news:
                if not article['thumbnail']:
                    article['thumbnail'] = ogs.get(article['link'])

    @staticmethod
    def get_thumbnail(entry: dict, description: str, no_thumbnail: List[str]) -> str:
        thumbnail = RSSParser.extract_thumbnail(entry)
        if not thumbnail:
            thumbnail = RSSParser.extract_image_from_description(description)
            if not thumbnail:
                no_thumbnail.append(entry.get('link'))
        return thumbnail

    @staticmethod
    def extract_thumbnail(entry: dict) -> str:
        if "media_thumbnail" in entry and entry["media_thumbnail"]:
            return entry["media_thumbnail"][0].get("url", "")

        if "media_content" in entry:
            for media in entry["media_content"]:
                if "url" in media:
                    return media["url"]

        if "enclosures" in entry:
            for enclosure in entry["enclosures"]:
                if enclosure.get("type", "").startswith("image/"):
                    return enclosure.get("href", "")

        content = entry.get("content", [{}])[0].get("value", "")
        img_match = re.search(r'<img[^>]+src="([^"]+)"', content)
        if img_match:
            return img_match.group(1)

        return ""

    @staticmethod
    def extract_image_from_description(description: str) -> str:
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
        results = await asyncio.gather(*(RSSParser.get_og(url, session) for url in urls))
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

    @staticmethod
    def clean_html(html_text: str) -> str:
        text = re.sub(r'</?p[^>]*>', '\n', html_text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&(#?\w+);', lambda m: html.unescape(m.group(0)), text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

# --------------------------
# Main Function
# --------------------------

async def main():
    semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
    async with aiohttp.ClientSession() as session:
        feeds = await Database.get_all_feeds()
        tasks = [RSSParser.process_feed(feed, session, semaphore) for feed in feeds]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())