# rss_feed_parser.py
import os
import re
import json
import random
import logging
import asyncio
import aiohttp
import feedparser
import hashlib
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List, Tuple
from aiohttp import ClientSession, TCPConnector
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import InsertOne
from utilities.helpers import proxy, retry

# ----------------------
# Config & Setup
# ----------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')

USER_AGENTS = [ua.strip() for ua in os.getenv('USER_AGENTS', '').split(',') if ua.strip()] or [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]
HEADERS = {"User-Agent": random.choice(USER_AGENTS)}

# ----------------------
# MongoDB Interface
# ----------------------
class Database:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['news']
    feeds = db['feeds']
    articles = db['articles']

    @staticmethod
    async def feed_exists(feed_url: str) -> bool:
        return await Database.feeds.count_documents({'feed_url': feed_url}, limit=1) > 0

    @staticmethod
    async def article_exists_bulk(links: List[str]) -> set:
        cursor = Database.articles.find({'link': {'$in': links}}, {'link': 1})
        return {doc['link'] async for doc in cursor}

    @staticmethod
    async def bulk_insert_articles(articles: List[dict]) -> int:
        if articles:
            ops = [InsertOne(article) for article in articles]
            result = await Database.articles.bulk_write(ops)
            logging.info(f"Inserted {result.inserted_count} articles.")
            return result.inserted_count
        return 0

    @staticmethod
    async def update_article_thumbnail(link: str, thumbnail_url: str):
        await Database.articles.update_one({'link': link}, {'$set': {'thumbnail': thumbnail_url}})

# ----------------------
# RSS Parsing Logic
# ----------------------
class RSSParser:
    semaphore = asyncio.Semaphore(10)

    @staticmethod
    @proxy
    @retry(retries=3, delay=1, backoff=2, jitter=True)
    async def fetch_feed(feed_url: str, session: ClientSession) -> Dict[str, Any]:
        async with session.get(feed_url) as resp:
            if resp.status != 200:
                return {"error": f"Failed to fetch RSS feed. Status: {resp.status}"}

            content = await resp.text()
            parsed = feedparser.parse(content)

            if parsed.bozo:
                return {"error": str(parsed.bozo_exception)}

            return {"feed": parsed.feed, "entries": parsed.entries, "status": "success"}

    @staticmethod
    async def process_feed(feed_url: str, session: ClientSession):
        data = await RSSParser.fetch_feed(feed_url, session)
        if "error" in data:
            logging.error(f"Failed to process feed {feed_url}: {data['error']}")
            return

        feed_id = await RSSParser.get_or_create_feed(feed_url, data['feed'])
        if feed_id:
            await RSSParser.process_articles(data['entries'], feed_id, session)

    @staticmethod
    async def get_or_create_feed(feed_url: str, feed_info: Dict[str, Any]):
        if await Database.feed_exists(feed_url):
            doc = await Database.feeds.find_one({'feed_url': feed_url})
            return doc['_id'] if doc else None

        feed_doc = {
            'feed_url': feed_url,
            'title': feed_info.get('title', 'Untitled Feed'),
            'description': feed_info.get('description', ''),
            'link': feed_info.get('link', ''),
            'language': feed_info.get('language', 'en'),
            'published': feed_info.get('published', ''),
            'image': RSSParser.extract_image(feed_info),
            'last_updated': datetime.now(UTC)
        }
        result = await Database.feeds.insert_one(feed_doc)
        return result.inserted_id

    @staticmethod
    def extract_image(feed_info: Dict[str, Any]) -> str:
        image = getattr(feed_info, 'image', '')
        if isinstance(image, str): return image
        if hasattr(image, 'href'): return image.href
        if isinstance(image, dict): return image.get('url', '')
        return ''

    @staticmethod
    async def process_articles(entries: List[Dict], feed_id: str, session: ClientSession):
        links = [entry.get('link', '') for entry in entries if entry.get('link')]
        existing_links = await Database.article_exists_bulk(links)

        now = datetime.now(UTC)
        need_og = []
        new_articles = []

        for entry in entries:
            link = entry.get('link', '')
            if not link or link in existing_links:
                continue

            thumb = RSSParser.extract_thumbnail(entry)
            if not thumb:
                need_og.append(link)

            article = {
                'feed_id': feed_id,
                'title': entry.get('title', 'No Title'),
                'description': entry.get('description', ''),
                'link': link,
                'published': RSSParser.parse_date(entry),
                'categories': RSSParser.extract_categories(entry),
                'thumbnail': thumb,
                'last_updated': now
            }
            new_articles.append(article)

        if need_og:
            og_images = await RSSParser.get_og_images(need_og, session)
            for article in new_articles:
                if not article['thumbnail']:
                    article['thumbnail'] = og_images.get(article['link'])

        await Database.bulk_insert_articles(new_articles)
        await RSSParser.validate_and_update_thumbnails(new_articles, session)

    @staticmethod
    async def validate_and_update_thumbnails(articles: List[Dict], session: ClientSession):
        for article in articles:
            thumb = article.get('thumbnail')
            if not thumb:
                continue
            if await RSSParser.validate_image_url(thumb, session):
                await Database.update_article_thumbnail(article['link'], thumb)
            else:
                imgs = RSSParser.extract_images_from_html(article.get('content', ''))
                for img in imgs:
                    if await RSSParser.validate_image_url(img, session):
                        await Database.update_article_thumbnail(article['link'], img)
                        break

    @staticmethod
    async def validate_image_url(url: str, session: ClientSession) -> bool:
        try:
            async with session.head(url, allow_redirects=True) as resp:
                ctype = resp.headers.get('Content-Type', '').lower()
                return resp.status == 200 and ctype.startswith('image/')
        except:
            return False

    @staticmethod
    async def get_og_images(urls: List[str], session: ClientSession) -> Dict[str, Optional[str]]:
        async def fetch(url: str):
            async with RSSParser.semaphore:
                try:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            return url, None
                        html = await resp.text()
                        match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html, re.I)
                        return url, match.group(1) if match else None
                except:
                    return url, None

        results = await asyncio.gather(*(fetch(u) for u in urls))
        return dict(results)

    @staticmethod
    def extract_thumbnail(entry: Dict[str, Any]) -> str:
        if hasattr(entry, 'media_thumbnail'):
            return entry.media_thumbnail[0].get('url', '')
        if hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if media.get('medium') == 'image':
                    return media.get('url', '')
        return ''

    @staticmethod
    def extract_images_from_html(html: str) -> List[str]:
        return re.findall(r'<img[^>]+src="([^"]+)"', html, re.I) if html else []

    @staticmethod
    def extract_categories(entry: Dict[str, Any]) -> List[str]:
        return [tag.term for tag in getattr(entry, 'tags', []) if hasattr(tag, 'term')]

    @staticmethod
    def parse_date(entry: Dict[str, Any]) -> str:
        for field in ['published', 'updated', 'pubDate']:
            if hasattr(entry, field):
                return getattr(entry, field)
        return 'N/A'

# ----------------------
# Entry Point
# ----------------------
async def main():
    rss_urls = [
        'https://www.aljazeera.com/xml/rss/all.xml',
        'https://www.cbsnews.com/latest/rss/main',
        'https://www.theguardian.com/us-news/rss',
        'https://mashable.com/feeds/rss/all',
        'https://www.theverge.com/rss/index.xml',
        'https://img.rtvslo.si/feeds/00.xml'
    ]

    random.shuffle(rss_urls)
    connector = TCPConnector(limit=20, limit_per_host=5)

    async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        tasks = [RSSParser.process_feed(url, session) for url in rss_urls]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass

    asyncio.run(main())
