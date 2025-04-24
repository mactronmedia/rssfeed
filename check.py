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

    @staticmethod
    async def get_all_feeds() -> List[Dict[str, Any]]:
        """Retrieve all feeds from the database, regardless of active status"""
        return await Database.feeds.find({}).to_list(length=None)

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
    async def insert_articles(docs: list) -> list:
        if docs:
            res = await Database.articles.insert_many(docs)
            logging.info(f"Inserted {len(res.inserted_ids)} articles.")
            return res.inserted_ids
        return []

    @staticmethod
    async def update_feed_last_checked(feed_id: str, last_checked: datetime):
        """Update the last checked timestamp for a feed."""
        await Database.feeds.update_one(
            {'_id': feed_id},
            {'$set': {'last_checked': last_checked}}
        )

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
            url = feed['feed_url']
            feed_id = feed['_id']
            
            logging.info(f"Processing feed: {url}")
            
            result = await RSSParser.fetch_feed(url, session)
            if "error" in result:
                logging.error(f"Feed error {url}: {result['error']}")
                await Database.update_feed_last_checked(feed_id, datetime.now(UTC))
                return

            entries = result["entries"]
            
            if not entries:
                logging.info(f"No entries found in feed: {url}")
                await Database.update_feed_last_checked(feed_id, datetime.now(UTC))
                return

            new_articles_added = await RSSParser.process_articles(entries, feed_id, session)

            if new_articles_added:
                await Database.feeds.update_one(
                    {'_id': feed_id}, 
                    {
                        '$set': {
                            'last_updated': datetime.now(UTC),
                            'last_checked': datetime.now(UTC)
                        }
                    }
                )
            else:
                await Database.update_feed_last_checked(feed_id, datetime.now(UTC))
                logging.info(f"No new articles found for feed: {url}")

    @staticmethod
    async def process_articles(entries: List[dict], feed_id: str, session: aiohttp.ClientSession) -> bool:
        articles = []
        no_thumbnail = []

        all_links = [entry.get('link') for entry in entries if entry.get('link')]
        existing_links = await Database.article_exists(all_links)

        for entry in entries:
            link = entry.get('link')
            if not link or link in existing_links:
                continue
            try:
                article = await RSSParser.process_entry(entry, feed_id, no_thumbnail)
                if article:
                    articles.append(article)
            except Exception as e:
                logging.error(f"Error processing entry: {e}")

        if no_thumbnail:
            ogs = await RSSParser.fetch_og_images(no_thumbnail, session)
            for article in articles:
                if not article['thumbnail']:
                    article['thumbnail'] = ogs.get(article['link'])

        inserted_ids = await Database.insert_articles(articles)
        return bool(inserted_ids)

    @staticmethod
    async def process_entry(entry: dict, feed_id: str, no_thumbnail: List[str]) -> dict | None:
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
            'language': article_language,
            'published': published,
            'link': link,
            'thumbnail': thumbnail,
        }

    @staticmethod
    def clean_html(html_text: str) -> str:
        text = re.sub(r'</?p[^>]*>', '\n', html_text)
        text = re.sub(r'<p[^>]*>', '\n', html_text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&(#?\w+);', lambda m: html.unescape(m.group(0)), text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

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
        results = await asyncio.gather(*(RSSParser.get_og(u, session) for u in urls))
        return dict(results)

    @staticmethod
    async def get_og(url: str, session: aiohttp.ClientSession) -> tuple:
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

async def main():
    start_time = time.time()

    # Get all feeds from the database (not just active ones)
    feeds = await Database.get_all_feeds()
    
    if not feeds:
        logging.warning("No feeds found in the database")
        return

    logging.info(f"Found {len(feeds)} feeds to process")
    
    semaphore = asyncio.Semaphore(5)  # Limit concurrency to 5 requests at a time

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(RSSParser.process_feed(feed, session, semaphore) for feed in feeds))

    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"Total execution time: {elapsed_time:.2f} seconds")


if __name__ == '__main__':
    asyncio.run(main())