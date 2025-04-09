import aiohttp
import feedparser
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

class FeedParser:
    @staticmethod
    async def fetch_feed(url: str) -> Dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                feed_content = await response.text()
                return feedparser.parse(feed_content)

    @staticmethod
    def parse_feed_metadata(feed_data: Dict) -> Dict:
        feed = feed_data.feed
        pub_date = feed.get("published_parsed")
        return {
            "title": feed.get("title", ""),
            "description": feed.get("description", ""),
            "link": feed.get("link", ""),
            "image": feed.get("image", {}).get("href", ""),
            "pubDate": datetime(*pub_date[:6]) if pub_date else datetime.utcnow(),
            "last_updated": datetime.utcnow(),
            "domain": urlparse(feed.get("link", "")).netloc
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
            
            items.append({
                "title": entry.get("title", ""),
                "description": entry.get("description", ""),
                "link": entry.get("link", ""),
                "pubDate": pub_date,  # Now stored as ISO format string
                "media_thumbnail": entry.get("media_thumbnail", [{}])[0].get("url", "") if "media_thumbnail" in entry else "",
                "feed_url": feed_url,
                "full_content": "",
                "is_full_content_fetched": False
            })
        return items