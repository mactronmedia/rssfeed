import re
import aiohttp
import feedparser
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

class FeedParser:
    @staticmethod
    async def fetch_feed(url: str) -> Dict:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                feed_content = await response.text()
                return feedparser.parse(feed_content)

    @staticmethod
    def parse_feed_metadata(feed_data: dict) -> dict:
        feed = feed_data.feed
        link = feed.get("link", "")
        return {
            "title": feed.get("title", ""),
            "description": feed.get("description", ""),
            "link": link,
            "image": feed.get("image", {}).get("href", ""),
            "pubDate": datetime(*feed.get("published_parsed", datetime.utcnow().timetuple())[:6]),
            "last_updated": datetime.utcnow(),
            "domain": urlparse(link).netloc if link else ""
        }

    @staticmethod
    @staticmethod
    def clean_html(html: str) -> str:
        # Simple method to clean HTML tags, can be adjusted as necessary
        clean = re.sub(r'<[^>]+>', '', html)
        return clean.strip()

    @staticmethod
    def parse_feed_items(feed_data, feed_url: str) -> List[dict]:
        items = []
        for entry in feed_data.entries:
            # Handle pubDate conversion
            pub_date = entry.get("published_parsed")
            if pub_date:
                pub_date = datetime(*pub_date[:6]).isoformat()
            else:
                pub_date = datetime.utcnow().isoformat()

            # Initialize media_thumbnail as an empty string
            media_thumbnail = ""

            # Check for media:content and extract URL if present
            if "media_content" in entry:
                media_contents = entry.get("media_content", [])
                media_contents.sort(key=lambda x: int(x.get("width", 0)), reverse=True)

                # Extract the URL from the largest image found (if any)
                if media_contents:
                    media_thumbnail = media_contents[0].get("url", "")

            # Fallback: Try extracting an image from enclosure
            if not media_thumbnail:
                enclosure = entry.get("enclosures", [])
                if enclosure:
                    media_thumbnail = enclosure[0].get("url", "")

            # Fallback: Try extracting an image from the description (HTML <img>)
            if not media_thumbnail:
                description = entry.get("description", "")
                match = re.search(r'<img[^>]+src="([^">]+)"', description)
                if match:
                    media_thumbnail = match.group(1)

            # Fallback: Try extracting an image from content:encoded (HTML <img>)
            if not media_thumbnail:
                content = entry.get("content", [{}])[0].get("value", "")
                match = re.search(r'<img[^>]+src="([^">]+)"', content)
                if match:
                    media_thumbnail = match.group(1)

            # Decode &amp; to & in the image URL if necessary
            if media_thumbnail:
                media_thumbnail = media_thumbnail.replace("&amp;", "&")

            # Clean and extract text from description (removing all HTML tags)
            description = entry.get("description", "")
            clean_description = FeedParser.clean_html(description)

            items.append({
                "title": entry.get("title", ""),
                "description": clean_description,  # Cleaned description
                "link": entry.get("link", ""),
                "pubDate": pub_date,
                "media_thumbnail": media_thumbnail,  # Store the valid image URL
                "feed_url": feed_url,
                "full_content": "",
                "is_full_content_fetched": False
            })

        return items

    @staticmethod
    def clean_html(content: str) -> str:
        cleaned = re.sub(r'<(?!p\s*[^>]*>)([^>]+)>', '', content)
        cleaned = re.sub(r'<p\s*[^>]*>', '\n', cleaned)
        cleaned = re.sub(r'</p>', '\n', cleaned)
        cleaned = re.sub(r'<(script|iframe)[^>]*>.*?</\1>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        cleaned = re.sub(r'\n+', '\n', cleaned).strip()
        
        return cleaned