# core/feed_parser

import re
import html
import time
import asyncio
import aiohttp
import feedparser
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
from selectolax.parser import HTMLParser  # Faster alternative to BeautifulSoup
from fastapi import HTTPException

class FeedParser:
    start_time = time.time()

    @staticmethod
    async def fetch_feed(url: str, session: aiohttp.ClientSession) -> Dict:
        """Fetch and parse RSS/Atom feed with timeout and retry logic"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml'
        }

        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Feed fetch failed")
                feed_content = await response.text()
                return feedparser.parse(feed_content)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Feed request timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Feed fetch error: {str(e)}")

    @staticmethod
    def parse_feed_metadata(feed_data: dict) -> dict:
        """Extract feed metadata with error handling"""
        feed = feed_data.feed
        link = feed.get("link", "")
        
        try:
            pub_date = datetime(*feed.get("published_parsed", datetime.utcnow().timetuple())[:6])
        except (TypeError, ValueError):
            pub_date = datetime.utcnow()

        return {
            "title": feed.get("title", ""),
            "description": feed.get("description", ""),
            "link": link,
            "image": feed.get("image", {}).get("href", ""),
            "pubDate": pub_date.isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "domain": urlparse(link).netloc if link else ""
        }

    @staticmethod
    async def parse_feed_items(feed_data, feed_url: str, session: aiohttp.ClientSession) -> List[dict]:
        """Parse feed items with parallel image fetching"""
        items = []
        article_fetch_tasks = []

        for entry in feed_data.entries:
            # Parse publication date
            pub_date = FeedParser.parse_item_pub_date(entry)
            
            # Extract media thumbnail
            media_thumbnail = await FeedParser.extract_media_thumbnail(entry, session)

            # Prepare the basic item
            item = FeedParser.prepare_item_dict(entry, pub_date, feed_url, media_thumbnail)
            items.append(item)

            # Fetch article images if necessary
            article_fetch_tasks.append(FeedParser.fetch_image_from_article(entry.get("link"), session))

        # Fetch all article images in parallel
        await FeedParser.fetch_article_images(items, article_fetch_tasks)

        return items

    @staticmethod
    def parse_item_pub_date(entry) -> str:
        """Parse publication date from feed entry"""
        pub_date = entry.get("published_parsed")
        try:
            return datetime(*pub_date[:6]).isoformat() if pub_date else datetime.utcnow().isoformat()
        except (TypeError, ValueError):
            return datetime.utcnow().isoformat()

    @staticmethod
    async def extract_media_thumbnail(entry, session) -> str:
        """Extract media thumbnail from entry with fallbacks"""
        media_thumbnail = ""

        # Try media_thumbnail first
        if "media_thumbnail" in entry:
            media_thumbnail = entry["media_thumbnail"][0].get("url", "")

        # If still not found, try media_content
        if not media_thumbnail and "media_content" in entry:
            for media in entry["media_content"]:
                if media.get("medium") == "image" and media.get("type", "").startswith("image/"):
                    media_thumbnail = media.get("url", "")
                    break

        # Fallback: try extracting from description
        if not media_thumbnail:
            media_thumbnail = FeedParser.extract_image_from_html(entry.get("description", ""))

        # Fallback: try extracting from content
        if not media_thumbnail:
            content = entry.get("content", [{}])[0].get("value", "")
            media_thumbnail = FeedParser.extract_image_from_html(content)

        # Fallback: try enclosures
        if not media_thumbnail:
            enclosure = entry.get("enclosures", [])
            media_thumbnail = enclosure[0].get("url", "") if enclosure else ""

        return media_thumbnail

    @staticmethod
    def extract_image_from_html(html_content: str) -> str:
        """Extract first image URL from HTML content with multiple fallback methods"""
        if not html_content:
            return ""
        
        img_match = re.search(r'<img[^>]+src=["\']([^"\'>]+)', html_content)
        if img_match:
            return img_match.group(1).split('"')[0].split("'")[0]
        
        try:
            tree = HTMLParser(html_content)
            img = tree.css_first("img")
            if img and img.attributes.get("src"):
                return img.attributes["src"]
        except Exception:
            pass
        
        return ""

    @staticmethod
    def prepare_item_dict(entry, pub_date, feed_url, media_thumbnail) -> dict:
        """Prepare the basic item dictionary"""
        return {
            "title": entry.get("title", ""),
            "description": FeedParser.clean_html(entry.get("description", "")),
            "link": entry.get("link", ""),
            "pubDate": pub_date,
            "media_thumbnail": media_thumbnail.replace("&amp;", "&") if media_thumbnail else "",
            "feed_url": feed_url,
            "full_content": "",
            "is_full_content_fetched": False
        }

    @staticmethod
    async def fetch_article_images(items, article_fetch_tasks) -> None:
        """Fetch article images in parallel"""
        article_images = await asyncio.gather(
            *[task for task in article_fetch_tasks if task is not None],
            return_exceptions=True
        )

        # Update items with fetched images
        img_index = 0
        for i, item in enumerate(items):
            if not item["media_thumbnail"] and article_fetch_tasks[i] is not None:
                if not isinstance(article_images[img_index], Exception):
                    item["media_thumbnail"] = article_images[img_index].replace("&amp;", "&")
                img_index += 1

    @staticmethod
    async def fetch_image_from_article(url: str, session: aiohttp.ClientSession) -> str:
        """Fetch article page and extract image URL with optimized parsing"""
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    # Only read the first 50KB - enough to find meta tags
                    content = await response.content.read(50000)
                    html = content.decode('utf-8', errors='ignore')
                    
                    # First try fast regex for Open Graph/Twitter images
                    og_match = re.search(r'<meta\s[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\'>]+)', html)
                    if og_match:
                        return og_match.group(1).split('"')[0].split("'")[0]
                    
                    twitter_match = re.search(r'<meta\s[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\'>]+)', html)
                    if twitter_match:
                        return twitter_match.group(1).split('"')[0].split("'")[0]
                    
                    # Fall back to selectolax for more complex parsing
                    try:
                        tree = HTMLParser(html)
                        
                        # Check Open Graph image again with proper parsing
                        og_image = tree.css_first('meta[property="og:image"]')
                        if og_image and og_image.attributes.get("content"):
                            return og_image.attributes["content"]
                            
                        # Check Twitter image
                        twitter_image = tree.css_first('meta[name="twitter:image"]')
                        if twitter_image and twitter_image.attributes.get("content"):
                            return twitter_image.attributes["content"]
                            
                        # Find first content image
                        img = tree.css_first("img")
                        if img and img.attributes.get("src"):
                            return img.attributes["src"]
                    except Exception:
                        pass
        except Exception as e:
            print(f"Failed to fetch image from article {url}: {str(e)}")
        
        return ""

    @staticmethod
    def clean_html(content: str) -> str:
        """Clean HTML content while preserving paragraphs"""
        if not content:
            return ""
            
        # Remove script and iframe tags
        cleaned = re.sub(r'<(script|iframe)[^>]*>.*?</\1>', '', content, flags=re.DOTALL)
        
        # Replace paragraphs with newlines
        cleaned = re.sub(r'</?p[^>]*>', '\n', cleaned)
        
        # Remove all other tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Normalize whitespace and clean up
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
        cleaned = cleaned.strip()
        
        return html.unescape(cleaned)

    @classmethod
    async def parse_feed(cls, feed_url: str) -> dict:
        """Main method to parse a complete feed with metadata and items"""
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            try:
                feed_data = await cls.fetch_feed(feed_url, session=session)
                metadata = cls.parse_feed_metadata(feed_data)
                items = await cls.parse_feed_items(feed_data, feed_url, session)
                
                return {
                    "metadata": metadata,
                    "items": items,
                    "processing_time": time.time() - start_time
                }
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse feed: {str(e)}"
                )

    print(f"Module loaded in {time.time() - start_time:.2f} seconds")