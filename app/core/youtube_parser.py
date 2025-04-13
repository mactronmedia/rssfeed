# core/youtube_parser.py

import re
import html
import time
import asyncio
import aiohttp
import feedparser
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
from selectolax.parser import HTMLParser
from fastapi import HTTPException
from app.schemas.youtube_feed import YouTubeFeedItem, YouTubeFeedResponse

class YouTubeFeedParser:
    start_time = time.time()

    @staticmethod
    async def fetch_feed(url: str, session: aiohttp.ClientSession) -> Dict:
        headers = {
            'User-Agent': 'Mozilla/5.0',
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
        feed = feed_data.feed
        link = feed.get("link", "")

        try:
            pub_date = datetime(*feed.get("published_parsed", datetime.utcnow().timetuple())[:6])
        except (TypeError, ValueError):
            pub_date = datetime.utcnow()

        return {
            "title": feed.get("title", ""),
            "description": feed.get("subtitle", ""),
            "link": link,
            "image": feed.get("image", {}).get("href", ""),
            "pubDate": pub_date.isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "domain": urlparse(link).netloc if link else ""
        }

    @staticmethod
    def parse_item_pub_date(entry) -> str:
        pub_date = entry.get("published_parsed")
        try:
            return datetime(*pub_date[:6]).isoformat() if pub_date else datetime.utcnow().isoformat()
        except (TypeError, ValueError):
            return datetime.utcnow().isoformat()

    @staticmethod
    def extract_image_from_html(html_content: str) -> str:
        if not html_content:
            return ""
        img_match = re.search(r'<img[^>]+src=["\']([^"\'>]+)', html_content)
        if img_match:
            return img_match.group(1)
        try:
            tree = HTMLParser(html_content)
            img = tree.css_first("img")
            if img and img.attributes.get("src"):
                return img.attributes["src"]
        except Exception:
            pass
        return ""

    @staticmethod
    def clean_html(content: str) -> str:
        if not content:
            return ""
        cleaned = re.sub(r'<(script|iframe)[^>]*>.*?</\1>', '', content, flags=re.DOTALL)
        cleaned = re.sub(r'</?p[^>]*>', '\n', cleaned)
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
        return html.unescape(cleaned.strip())

    @staticmethod
    def prepare_youtube_item(entry, pub_date, feed_url) -> dict:
        video_id = entry.get("yt_videoid") or entry.get("id", "").split(":")[-1]
        thumbnail = ""

        # YouTube-specific thumbnails
        if "media_thumbnail" in entry:
            thumbnail = entry["media_thumbnail"][0].get("url", "")
        elif "media_group" in entry:
            thumbnail = entry["media_group"].get("media_thumbnail", [{}])[0].get("url", "")

        # Fallback to manual extraction
        if not thumbnail:
            thumbnail = YouTubeFeedParser.extract_image_from_html(entry.get("description", ""))

        return {
            "title": entry.get("title", ""),
            "description": YouTubeFeedParser.clean_html(entry.get("media_description", entry.get("summary", ""))),
            "link": entry.get("link", f"https://www.youtube.com/watch?v={video_id}"),
            "pubDate": pub_date,
            "media_thumbnail": thumbnail.replace("&amp;", "&"),
            "feed_url": feed_url,
            "video_id": video_id,
            "is_full_content_fetched": False,
            "full_content": ""
        }

    @classmethod
    async def parse_feed(cls, feed_url: str) -> YouTubeFeedResponse:
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            try:
                feed_data = await cls.fetch_feed(feed_url, session=session)

                channel_id = None
                parsed_url = urlparse(feed_url)
                if parsed_url.query:
                    query_parts = dict(qc.split("=") for qc in parsed_url.query.split("&") if "=" in qc)
                    channel_id = query_parts.get("channel_id", "unknown")

                items: List[YouTubeFeedItem] = []
                for entry in feed_data.entries:
                    pub_date = cls.parse_item_pub_date(entry)
                    video_id = entry.get("yt_videoid") or entry.get("id", "").split(":")[-1]

                    # Extract thumbnail
                    thumbnail = ""
                    if "media_thumbnail" in entry:
                        thumbnail = entry["media_thumbnail"][0].get("url", "")
                    elif "media_group" in entry:
                        thumbnail = entry["media_group"].get("media_thumbnail", [{}])[0].get("url", "")

                    if not thumbnail:
                        thumbnail = cls.extract_image_from_html(entry.get("description", ""))

                    items.append(YouTubeFeedItem(
                        title=entry.get("title", ""),
                        link=entry.get("link", f"https://www.youtube.com/watch?v={video_id}"),
                        pubDate=pub_date,
                        thumbnail=thumbnail.replace("&amp;", "&"),
                        channel_id=channel_id,
                        fetched_at=datetime.utcnow(),
                    ))

                return YouTubeFeedResponse(
                    items=items,
                    channel_id=channel_id,
                    fetched_at=datetime.utcnow().isoformat()
                )

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to parse YouTube feed: {str(e)}")
            