import os
import re
import random
import logging
from typing import Optional, Dict

import aiohttp
from aiohttp import ClientSession
from lxml import html as lxml_html
from selectolax.parser import HTMLParser
import feedparser
import json

# Setup logging level from env variable
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("YouTubeChannel")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (X11; Linux x86_64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5)...",
    # Add more if needed
]

def get_random_headers() -> dict:
    return {"User-Agent": random.choice(USER_AGENTS)}

class YouTubeChannel:
    @staticmethod
    async def get_channel_info(entry: str) -> Dict[str, str]:
        entry = YouTubeChannel.normalize_entry(entry)

        if YouTubeChannel.is_rss_feed(entry):
            return await YouTubeChannel.process_rss_feed(entry)

        async with aiohttp.ClientSession() as session:
            html = await YouTubeChannel.fetch_page(session, entry)
            if not html:
                return {"error": "Failed to retrieve channel page."}

            feed_url = YouTubeChannel.extract_feed_url(html) or YouTubeChannel.fallback_feed_url_from_json(html)
            if not feed_url:
                return {"error": "RSS feed link not found on the channel page."}

            channel_id = YouTubeChannel.get_channel_id_from_rss(feed_url)
            if not channel_id:
                return {"error": "Channel ID not found in the RSS feed URL."}

            feed_data = feedparser.parse(feed_url)
            channel_title = feed_data.feed.get('title', 'Unknown') if feed_data and feed_data.feed else 'Unknown'

            return {
                "channel_id": channel_id,
                "feed_url": feed_url,
                "channel_title": channel_title,
                "source": "html_parsed"
            }

    @staticmethod
    def is_rss_feed(entry: str) -> bool:
        return "feeds/videos.xml?channel_id=" in entry

    @staticmethod
    async def process_rss_feed(entry: str) -> Dict[str, str]:
        channel_id = YouTubeChannel.get_channel_id_from_rss(entry)
        feed_data = feedparser.parse(entry)
        title = feed_data.feed.get("title", "Unknown") if feed_data and feed_data.feed else "Unknown"

        if channel_id:
            return {
                "channel_id": channel_id,
                "feed_url": entry,
                "channel_title": title,
                "source": "direct_rss"
            }
        return {"error": "Invalid RSS feed URL format."}

    @staticmethod
    def normalize_entry(entry: str) -> str:
        if entry.startswith('@'):
            return f"https://www.youtube.com/{entry}"
        if entry.startswith(('/user/', '/c/', '/channel/')):
            return f"https://www.youtube.com{entry}"
        if not entry.startswith('http'):
            return f"https://www.youtube.com/{entry}"
        return entry

    @staticmethod
    async def fetch_page(session: ClientSession, url: str) -> Optional[str]:
        try:
            async with session.get(url, headers=get_random_headers(), timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}, status code: {response.status}")
                    return None

                html = await response.text()

                if 'itemprop' not in html and 'consent.youtube.com' in html:
                    return await YouTubeChannel.handle_consent(session, html)

                return html

        except aiohttp.ClientError as e:
            logger.error(f"Client error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error during fetch: {e}")
        return None

    @staticmethod
    async def handle_consent(session: ClientSession, html: str) -> Optional[str]:
        try:
            parser = HTMLParser(html)
            form = parser.css_first('form')
            if not form:
                logger.warning("Consent form not found")
                return None

            post_url = form.attributes.get('action')
            if not post_url:
                return None

            form_data = {
                input_tag.attributes['name']: input_tag.attributes.get('value', '')
                for input_tag in form.css('input')
                if 'name' in input_tag.attributes
            }

            async with session.post(post_url, data=form_data, timeout=10, headers=get_random_headers()) as response:
                return await response.text() if response.status == 200 else None

        except Exception as e:
            logger.exception(f"Error handling consent: {e}")
        return None

    @staticmethod
    def extract_feed_url(html: str) -> Optional[str]:
        try:
            tree = lxml_html.fromstring(html)
            rss_link = tree.xpath('//link[@rel="alternate" and @type="application/rss+xml"]')
            return rss_link[0].attrib['href'] if rss_link else None
        except Exception as e:
            logger.exception(f"Error extracting feed URL: {e}")
            return None

    @staticmethod
    def fallback_feed_url_from_json(html: str) -> Optional[str]:
        try:
            yt_initial_data = re.search(r'var ytInitialData = ({.*?});', html)
            if yt_initial_data:
                json_data = json.loads(yt_initial_data.group(1))
                # Not actually extracting channel ID here, just showing possible fallback
                logger.debug("ytInitialData fallback found, but not implemented fully.")
        except Exception as e:
            logger.warning("Fallback via ytInitialData failed: %s", e)
        return None

    @staticmethod
    def get_channel_id_from_rss(feed_url: str) -> Optional[str]:
        try:
            match = re.search(r'channel_id=([A-Za-z0-9_-]+)', feed_url)
            if match:
                channel_id = match.group(1)
                logger.info(f"Extracted channel ID: {channel_id}")
                return channel_id
        except Exception as e:
            logger.exception(f"Error extracting channel ID: {e}")
        return None

# --- CLI usage for testing ---

if __name__ == "__main__":
    import asyncio

    async def main():
        entry = 'Google'
        result = await YouTubeChannel.get_channel_info(entry)

        if 'error' in result:
            logger.error(f"❌ Error: {result['error']}")
        else:
            logger.info("✅ Success!")
            logger.info(f"Channel ID    : {result['channel_id']}")
            logger.info(f"Channel Title : {result['channel_title']}")
            logger.info(f"Feed URL      : {result['feed_url']}")
            logger.info(f"Source        : {result['source']}")

    asyncio.run(main())
