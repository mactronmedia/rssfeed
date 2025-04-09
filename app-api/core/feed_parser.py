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
    def parse_feed_items(feed_data, feed_url: str) -> list[dict]:
        items = []
        for entry in feed_data.entries:
            # Handle pubDate conversion
            pub_date = entry.get("published_parsed")
            if pub_date:
                pub_date = datetime(*pub_date[:6]).isoformat()
            else:
                pub_date = datetime.utcnow().isoformat()

            # Get media thumbnail if available
            media_thumbnail = entry.get("media_thumbnail", [{}])[0].get("url", "") if "media_thumbnail" in entry else ""

            # Fallback: try to extract image from description if thumbnail is missing
            if not media_thumbnail:
                description = entry.get("description", "")
                match = re.search(r'<img[^>]+src="([^">]+)"', description)
                if match:
                    media_thumbnail = match.group(1)

            items.append({
                "title": entry.get("title", ""),
                "description": entry.get("description", ""),
                "link": entry.get("link", ""),
                "pubDate": pub_date,
                "media_thumbnail": media_thumbnail,
                "feed_url": feed_url,
                "full_content": "",
                "is_full_content_fetched": False
            })
        return items