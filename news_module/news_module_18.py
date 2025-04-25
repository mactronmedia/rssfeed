import os
import re
import html
import json
import aiohttp
import asyncio
import logging
import random
import feedparser
from datetime import datetime, UTC
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any, List, Tuple
from utilities.helpers import proxy, retry

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')

USER_AGENTS = [ua.strip() for ua in os.getenv('USER_AGENTS', '').split(',') if ua.strip()] or [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]
HEADERS = {"User-Agent": random.choice(USER_AGENTS)}

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

    @staticmethod
    async def update_thumbnail(link: str, url: str):
        await Database.articles.update_one({'link': link}, {'$set': {'thumbnail': url}})

# RSS Logic
class RSSParser:
    @staticmethod
    @retry(retries=3, delay=1, backoff=2, jitter=True)
    @proxy 
    async def fetch_feed(url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        try:
            async with session.get(url) as response:
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
        if await Database.feed_exists(url):
            logging.info(f"Feed {url} already exists. Skipping feed.")
            return

        result = await RSSParser.fetch_feed(url, session)
        if "error" in result:
            logging.error(f"Feed error {url}: {result['error']}")
            return

        feed_id = await RSSParser.get_or_create_feed(url, result["feed"])
        if feed_id:
            await RSSParser.process_articles(result["entries"], feed_id, session)

    @staticmethod
    async def get_or_create_feed(url: str, feed_data: dict):
        try:
            feed_data = {
                'feed_url': url,
                'title': feed_data.get('title', 'Untitled'),
                'description': feed_data.get('description', ''),
                'link': feed_data.get('link', ''),
                'language': feed_data.get('language', 'en'),
                'published': feed_data.get('published', ''),
                'image': RSSParser.parse_image(feed_data),
                'last_updated': datetime.now(UTC),
            }
            result = await Database.feeds.insert_one(feed_data)
            logging.info(f"Feed {url} inserted successfully.")
            return result.inserted_id
        except Exception as e:
            logging.error(f"Error inserting feed {url}: {str(e)}")
            return None  

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
        articles, no_thumbnail = [], []

        for entry in entries:
            link = entry.get('link')
            if not link or await Database.article_exists(link):
                continue

            thumbnail = RSSParser.extract_thumbnail(entry)
            if not thumbnail:
                no_thumbnail.append(link)

            articles.append({
                'feed_id': feed_id,
                'title': entry.get('title', 'No Title'),
                'description': RSSParser.clean_html(entry.get('description', '')),
                'link': link,
                'published': RSSParser.get_pub_date(entry),
                'thumbnail': thumbnail,
                'last_updated': datetime.now(UTC)
            })

        # Fetch OG images if needed
        if no_thumbnail:
            ogs = await RSSParser.fetch_og_images(no_thumbnail, session)
            for a in articles:
                if not a['thumbnail']:
                    a['thumbnail'] = ogs.get(a['link'])

        await Database.insert_articles(articles)
        await RSSParser.verify_thumbnails(articles, session)

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
        for key in ['media_thumbnail', 'image', 'media_content']:
            if key in entry:
                val = entry[key]
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    return val[0].get('url', '')
                if isinstance(val, dict):
                    return val.get('url', '')
                if isinstance(val, str):
                    return val
        return ''

    @staticmethod
    def get_pub_date(entry: dict) -> str:
        for k in ['published', 'updated', 'pubDate', 'dc_date']:
            if val := entry.get(k):
                return val
        return 'N/A'

    @staticmethod
    async def verify_thumbnails(articles: List[dict], session: aiohttp.ClientSession):
        for article in articles:
            url = article.get('thumbnail')
            if not url:
                continue
            valid = await RSSParser.check_image(url, session)
            if not valid:
                images = RSSParser.extract_images(article.get('description', ''))
                for img_url in images:
                    if await RSSParser.check_image(img_url, session):
                        await Database.update_thumbnail(article['link'], img_url)
                        break

    @staticmethod
    async def check_image(url: str, session: aiohttp.ClientSession) -> bool:
        try:
            async with session.head(url, allow_redirects=True, timeout=5) as r:
                return r.status == 200 and r.headers.get('Content-Type', '').startswith('image')
        except:
            return False

    @staticmethod
    def extract_images(html: str) -> List[str]:
        return re.findall(r'<img[^>]+src="([^">]+)"', html, re.I)

    @staticmethod
    async def fetch_og_images(urls: List[str], session: aiohttp.ClientSession) -> Dict[str, Optional[str]]:
        async def get_og(url):
            try:
                async with session.get(url, timeout=10) as r:
                    if r.status != 200:
                        return url, None
                    html = await r.text()
                    match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^">]+)"', html, re.I)
                    return url, match.group(1) if match else None
            except:
                return url, None
        results = await asyncio.gather(*(get_og(u) for u in urls))
        return dict(results)

# Entry point
async def main():
    rss_urls = [

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
            'https://www.wired.com/feed'
            
        ]

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        await asyncio.gather(*(RSSParser.process_feed(url, session) for url in rss_urls))

if __name__ == '__main__':
    asyncio.run(main())