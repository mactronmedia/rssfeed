from lxml import etree
import aiohttp
import feedparser
from io import BytesIO
from datetime import datetime
from typing import Dict, List
import re

class FeedParser:
    @staticmethod
    async def fetch_feed(url: str) -> Dict:
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                raw = await response.read()
                parsed = feedparser.parse(raw)
                return {
                    "raw": raw,
                    "parsed": parsed
                }

    @staticmethod
    def parse_feed_metadata(feed_data: dict) -> dict:
        feed = feed_data["parsed"].feed
        link = feed.get("link", "")
        return {
            "title": feed.get("title", ""),
            "description": feed.get("description", ""),
            "link": link,
            "image": feed.get("image", {}).get("href", ""),
            "pubDate": datetime(*feed.get("published_parsed", datetime.utcnow().timetuple())[:6]),
            "last_updated": datetime.utcnow(),
            "domain": link.split("/")[2] if link else ""
        }

    @staticmethod
    def parse_feed_items(feed_data: dict, feed_url: str) -> List[dict]:
        parsed = feed_data["parsed"]
        raw_xml = feed_data["raw"]
        xml_root = etree.parse(BytesIO(raw_xml))

        # map GUIDs or links to raw <image> tags
        custom_images = {}
        for item in xml_root.xpath("//item"):
            link = item.findtext("link") or item.findtext("guid")
            image = item.findtext("image")
            if link and image:
                custom_images[link.strip()] = image.strip()

        items = []
        for entry in parsed.entries:
            pub_date = entry.get("published_parsed")
            pub_date = datetime(*pub_date[:6]).isoformat() if pub_date else datetime.utcnow().isoformat()

            media_thumbnail = entry.get("media_thumbnail", [{}])[0].get("url", "")

            if not media_thumbnail:
                # try <image> tag from custom mapping
                media_thumbnail = custom_images.get(entry.get("link", "").strip(), "")

            if not media_thumbnail:
                description = entry.get("description", "")
                match = re.search(r'<img[^>]+src="([^">]+)"', description)
                if match:
                    media_thumbnail = match.group(1)

            if not media_thumbnail:
                content = entry.get("content", [{}])[0].get("value", "")
                match = re.search(r'<img[^>]+src="([^">]+)"', content)
                if match:
                    media_thumbnail = match.group(1)

            if not media_thumbnail:
                enclosures = entry.get("enclosures", [])
                if enclosures:
                    media_thumbnail = enclosures[0].get("url", "")

            if media_thumbnail:
                media_thumbnail = media_thumbnail.replace("&amp;", "&")

            clean_description = FeedParser.clean_html(entry.get("description", ""))

            items.append({
                "title": entry.get("title", ""),
                "description": clean_description,
                "link": entry.get("link", ""),
                "pubDate": pub_date,
                "media_thumbnail": media_thumbnail,
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
