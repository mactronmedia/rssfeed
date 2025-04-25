import os
import re
import json
import aiohttp
import asyncio
import logging
import random
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict, List, Any
from aiohttp import ClientSession
from lxml import html as lxml_html
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from selectolax.parser import HTMLParser
from utilities.helpers import retry, proxy

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from environment variables
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
    db = client['news_database']
    collection_sources = db['sources']
    collection_articles = db['articles']

    @staticmethod
    async def source_exists(source_url: str) -> bool:
        doc = await Database.collection_sources.find_one({'base_url': source_url})
        return doc is not None

    @staticmethod
    async def article_exists(article_url: str) -> bool:
        doc = await Database.collection_articles.find_one({'url': article_url})
        return doc is not None

    @staticmethod
    async def bulk_insert_articles(article_data_list: List[Dict[str, Any]]) -> List[ObjectId]:
        if article_data_list:
            result = await Database.collection_articles.insert_many(article_data_list)
            logging.info(f"Inserted {len(result.inserted_ids)} articles.")
            return result.inserted_ids
        return []

class NewsSource:
    @staticmethod
    def is_valid_news_url(url: str) -> bool:
        """Validate that the URL belongs to a known news domain."""
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            
            # List of known news domains
            valid_hosts = (
                "bbc.com", "www.bbc.com", "bbc.co.uk", "www.bbc.co.uk",
                "cnn.com", "www.cnn.com",
                "nytimes.com", "www.nytimes.com",
                "theguardian.com", "www.theguardian.com",
                "reuters.com", "www.reuters.com"
            )
            
            return any(netloc == host or netloc.endswith(f".{host}") for host in valid_hosts)
        except Exception as e:
            logging.error(f"URL validation error: {e}")
            return False

    @staticmethod
    async def get_source_info(url: str, session: ClientSession) -> Dict[str, Any]:
        """Retrieve basic information about a news source."""
        if not NewsSource.is_valid_news_url(url):
            return {"error": f"Invalid news URL: {url}"}

        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        if await Database.source_exists(base_url):
            existing_source = await Database.collection_sources.find_one({'base_url': base_url})
            return {
                "source_id": str(existing_source['_id']),
                "base_url": base_url,
                "name": existing_source.get('name', ''),
                "source": "existing"
            }

        # Fetch the homepage to extract source info
        html = await NewsFetcher.fetch_page(url, session)
        if not html:
            return {"error": "Failed to retrieve source page."}

        source_info = NewsParser.extract_source_info(html, base_url)
        
        if not source_info.get('name'):
            source_info['name'] = urlparse(base_url).netloc.split('.')[-2].capitalize()

        # Insert the new source
        result = await Database.collection_sources.insert_one(source_info)
        return {
            "source_id": str(result.inserted_id),
            "base_url": base_url,
            "name": source_info['name'],
            "source": "new"
        }

class NewsFetcher:
    @staticmethod
    @proxy
    @retry(retries=3, delay=1, backoff=2, jitter=True)
    async def fetch_page(url: str, session: ClientSession) -> Optional[str]:
        """Fetch page content with error handling."""
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Failed to fetch {url}: Status {response.status}")
                    return None
                return await response.text()
        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
            return None

    @staticmethod
    async def fetch_article_list(source_url: str, session: ClientSession) -> List[str]:
        """Fetch list of article URLs from a news source homepage or section page."""
        html = await NewsFetcher.fetch_page(source_url, session)
        if not html:
            return []
        
        return NewsParser.extract_article_links(html, source_url)

class NewsParser:
    @staticmethod
    def extract_source_info(html: str, base_url: str) -> Dict[str, Any]:
        """Extract news source information from HTML."""
        try:
            tree = lxml_html.fromstring(html)
            
            # Try to get the site name from various meta tags
            name = None
            for xpath in [
                '//meta[@property="og:site_name"]/@content',
                '//meta[@name="application-name"]/@content',
                '//title/text()'
            ]:
                result = tree.xpath(xpath)
                if result:
                    name = result[0].strip()
                    break
            
            # Get favicon
            favicon = None
            for xpath in [
                '//link[@rel="icon" or @rel="shortcut icon"]/@href',
                '//meta[@itemprop="image"]/@content'
            ]:
                result = tree.xpath(xpath)
                if result:
                    favicon = urljoin(base_url, result[0])
                    break
            
            return {
                'base_url': base_url,
                'name': name,
                'favicon': favicon,
                'last_updated': datetime.utcnow()
            }
        except Exception as e:
            logging.error(f"Error extracting source info: {e}")
            return {'base_url': base_url, 'last_updated': datetime.utcnow()}

    @staticmethod
    def extract_article_links(html: str, base_url: str) -> List[str]:
        """Extract article links from a news page."""
        try:
            tree = lxml_html.fromstring(html)
            
            # Common patterns for news article links
            article_links = set()
            
            # XPaths that might match article links
            xpaths = [
                '//a[contains(@href, "/article/")]/@href',
                '//a[contains(@href, "/news/")]/@href',
                '//a[contains(@href, "/story/")]/@href',
                '//a[contains(@class, "card")]/@href',
                '//a[contains(@class, "headline")]/@href',
                '//article//a/@href',
                '//h3/a/@href'
            ]
            
            for xpath in xpaths:
                links = tree.xpath(xpath)
                for link in links:
                    if not link or link.startswith(('#', 'javascript:', 'mailto:')):
                        continue
                    
                    # Make absolute URL if relative
                    full_url = urljoin(base_url, link.split('?')[0].split('#')[0])
                    
                    # Basic filtering to ensure it's likely an article URL
                    if any(part in full_url.lower() for part in ['article', 'news', 'story', '20']):
                        article_links.add(full_url)
            
            return list(article_links)
        except Exception as e:
            logging.error(f"Error extracting article links: {e}")
            return []

    @staticmethod
    def parse_article(html: str, url: str) -> Dict[str, Any]:
        """Parse article content from HTML."""
        try:
            tree = lxml_html.fromstring(html)
            
            # Extract title
            title = None
            for xpath in [
                '//h1/text()',
                '//h1//text()',
                '//meta[@property="og:title"]/@content',
                '//title/text()'
            ]:
                result = tree.xpath(xpath)
                if result:
                    title = ' '.join(result[0].strip().split())
                    break
            
            # Extract publication date
            pub_date = None
            for xpath in [
                '//meta[@property="article:published_time"]/@content',
                '//time/@datetime',
                '//span[@class="date"]/text()',
                '//div[contains(@class, "timestamp")]/text()'
            ]:
                result = tree.xpath(xpath)
                if result:
                    pub_date = result[0].strip()
                    break
            
            # Extract author
            author = None
            for xpath in [
                '//meta[@name="author"]/@content',
                '//span[@class="author"]/text()',
                '//a[contains(@class, "author")]/text()',
                '//div[contains(@class, "byline")]//text()'
            ]:
                result = tree.xpath(xpath)
                if result:
                    author = ' '.join(result[0].strip().split())
                    break
            
            # Extract main content
            content = []
            for xpath in [
                '//article//p',
                '//div[contains(@class, "article-body")]//p',
                '//div[@itemprop="articleBody"]//p'
            ]:
                paragraphs = tree.xpath(xpath)
                if paragraphs:
                    for p in paragraphs:
                        text = ' '.join(p.xpath('.//text()')).strip()
                        if text:
                            content.append(text)
                    break
            
            # Extract image
            image = None
            for xpath in [
                '//meta[@property="og:image"]/@content',
                '//figure//img/@src',
                '//div[contains(@class, "article-image")]//img/@src'
            ]:
                result = tree.xpath(xpath)
                if result:
                    image = urljoin(url, result[0])
                    break
            
            return {
                'title': title,
                'url': url,
                'published_date': pub_date,
                'author': author,
                'content': '\n\n'.join(content),
                'image_url': image,
                'scraped_at': datetime.utcnow()
            }
        except Exception as e:
            logging.error(f"Error parsing article {url}: {e}")
            return {'url': url, 'scraped_at': datetime.utcnow()}

class NewsScraper:
    @staticmethod
    async def scrape_source(source_url: str, session: ClientSession):
        """Scrape all articles from a news source."""
        source_info = await NewsSource.get_source_info(source_url, session)
        if 'error' in source_info:
            logging.error(source_info['error'])
            return
        
        article_urls = await NewsFetcher.fetch_article_list(source_url, session)
        logging.info(f"Found {len(article_urls)} articles at {source_url}")
        
        tasks = []
        for url in article_urls:
            tasks.append(NewsScraper.process_article(url, session, source_info['source_id']))
        
        # Process in batches to avoid overwhelming the server
        for i in range(0, len(tasks), 10):  # Batch size of 10
            batch = tasks[i:i+10]
            await asyncio.gather(*batch)
            await asyncio.sleep(1)  # Be polite with delay between batches

    @staticmethod
    async def process_article(url: str, session: ClientSession, source_id: str) -> Optional[Dict[str, Any]]:
        """Process a single article URL."""
        if await Database.article_exists(url):
            logging.info(f"Article {url} already exists. Skipping.")
            return None
        
        html = await NewsFetcher.fetch_page(url, session)
        if not html:
            return None
        
        article_data = NewsParser.parse_article(html, url)
        article_data['source_id'] = source_id
        
        try:
            await Database.collection_articles.insert_one(article_data)
            logging.info(f"Inserted article: {article_data.get('title', url)}")
            return article_data
        except Exception as e:
            logging.error(f"Error saving article {url}: {e}")
            return None

async def main():
    async with aiohttp.ClientSession(headers=headers) as session:
        # Example usage - can be modified to accept URLs as arguments
        sources = [
            "https://www.bbc.com/news",
            #"https://www.cnn.com",
            #"https://www.nytimes.com"
        ]
        
        for source in sources:
            await NewsScraper.scrape_source(source, session)

if __name__ == "__main__":
    asyncio.run(main())