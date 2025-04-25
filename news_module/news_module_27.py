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

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
USER_AGENTS = [ua.strip() for ua in os.getenv('USER_AGENTS', '').split(',') if ua.strip()] or [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]
def get_random_headers() -> dict:
    return {"User-Agent": random.choice(USER_AGENTS)}

# Database class
class Database:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['news']
    feeds = db['feeds']
    articles = db['articles']

    @staticmethod
    async def feed_exists(url: str) -> bool:
        return await Database.feeds.find_one({'feed_url': url}) is not None

    @staticmethod
    async def article_exists(link: str) -> bool:
        return await Database.articles.find_one({'link': link}) is not None

    @staticmethod
    async def insert_articles(docs: list) -> list:
        if docs:
            res = await Database.articles.insert_many(docs)
            logging.info(f"Inserted {len(res.inserted_ids)} articles.")
            return res.inserted_ids
        return []

# RSS Parser with language detection
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
    async def process_feed(url: str, session: aiohttp.ClientSession):
        result = await RSSParser.fetch_feed(url, session)
        if "error" in result:
            logging.error(f"Feed error {url}: {result['error']}")
            return

        feed = await RSSParser.get_or_create_feed(url, result["feed"])
        if feed:
            await RSSParser.process_articles(result["entries"], feed, session)

    @staticmethod
    async def get_or_create_feed(url: str, feed_data: dict):
        existing = await Database.feeds.find_one({'feed_url': url})
        if existing:
            logging.info(f"Feed {url} already exists. Skipping feed save.")
            return existing.get('_id')
                        
        new_feed = {
            'feed_url': url,
            'title': feed_data.get('title', 'Untitled'),
            'description': feed_data.get('description', ''),
            'link': feed_data.get('link', ''),
            'language': 'feed_language',  # Use the passed feed_language
            'published': feed_data.get('published', ''),
            'image': RSSParser.parse_image(feed_data),
            'last_updated': datetime.now(UTC),
        }
        result = await Database.feeds.insert_one(new_feed)
        return result.inserted_id

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
    async def process_articles(entries: List[dict], feed_id, session: aiohttp.ClientSession):
        articles = []
        no_thumbnail = []

        for entry in entries:
            try:
                article = await RSSParser.process_entry(entry, feed_id, no_thumbnail)
                if article:
                    articles.append(article)
            except Exception as e:
                print(f"Error processing entry: {e}")

        if no_thumbnail:
            ogs = await RSSParser.fetch_og_images(no_thumbnail, session)
            for article in articles:
                if not article['thumbnail']:
                    article['thumbnail'] = ogs.get(article['link'])

        await Database.insert_articles(articles)

    @staticmethod
    async def process_entry(entry: dict, feed_id: int, no_thumbnail: List[str]) -> dict | None:
        link = entry.get('link')
        if not link or await Database.article_exists(link):
            return None

        description = entry.get('description', '')
        published = datetime(*entry.get("published_parsed", datetime.now(UTC).timetuple())[:6])
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
            'published': published,
            'link': link,
            'thumbnail': thumbnail,
            'language': article_language,
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
    async def get_og(url: str, session: aiohttp.ClientSession) -> tuple:
        try:
            print(f' {url} og')
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

        'https://www.index.hr/rss',
        'https://www.24sata.hr/feeds/aktualno.xml',
        'https://dnevnik.hr/assets/feed/articles',
        'https://www.croatiaweek.com/feed/',
        'https://total-croatia-news.com/feed/',

      
    ]
    
    # Limit concurrency using asyncio.Semaphore
    #semaphore = asyncio.Semaphore(5)  # Limit number of concurrent requests

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(RSSParser.process_feed(url, session) for url in rss_urls))

    end_time = time.time()  # End measuring time
    elapsed_time = end_time - start_time  # Calculate elapsed time
    print(f"Total execution time: {elapsed_time:.2f} seconds")  # Print the total time

if __name__ == '__main__':
    asyncio.run(main())
