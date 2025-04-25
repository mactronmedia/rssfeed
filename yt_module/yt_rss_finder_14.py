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

# Setup logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("YouTubeChannel")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
]

def get_random_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

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

            # First try to get info from JSON data
            json_data = YouTubeChannel.extract_info_from_json(html)
            if json_data:
                return json_data

            # Fallback to RSS feed extraction
            feed_url = YouTubeChannel.extract_feed_url(html)
            if not feed_url:
                return {"error": "RSS feed link not found on the channel page."}

            channel_id = YouTubeChannel.get_channel_id_from_rss(feed_url)
            if not channel_id:
                return {"error": "Channel ID not found in the RSS feed URL."}

            # Get additional info from RSS feed
            feed_data = feedparser.parse(feed_url)
            channel_title = feed_data.feed.get('title', 'Unknown') if feed_data and feed_data.feed else 'Unknown'
            avatar_url = feed_data.feed.get('icon', None)

            return {
                "channel_id": channel_id,
                "feed_url": feed_url,
                "channel_title": channel_title,
                "avatar_url": avatar_url,
                "source": "html_parsed"
            }

    @staticmethod
    def extract_info_from_json(html: str) -> Optional[Dict[str, str]]:
        """Main method to extract channel info from YouTube's JSON data."""
        try:
            json_data = YouTubeChannel.extract_yt_initial_data(html)
            if not json_data:
                return None

            # Extract basic channel info
            channel_id, channel_title = YouTubeChannel.extract_basic_info(json_data)
            if not channel_id:
                return None

            # Extract avatar URL
            avatar_url = YouTubeChannel.extract_avatar_url(json_data)
            
            return {
                "channel_id": channel_id,
                "feed_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
                "channel_title": channel_title,
                "avatar_url": avatar_url,
                "source": "yt_initial_data"
            }
        except Exception as e:
            logger.warning(f"Error parsing ytInitialData: {e}")
            return None

    @staticmethod
    def extract_yt_initial_data(html: str) -> Optional[dict]:
        """Extract ytInitialData from HTML."""
        yt_initial_data = re.search(r'var ytInitialData\s*=\s*({.*?});', html, re.DOTALL)
        if not yt_initial_data:
            return None
        return json.loads(yt_initial_data.group(1))

    @staticmethod
    def extract_basic_info(json_data: dict) -> tuple:
        """Extract channel ID and title from various locations in the JSON."""
        # Try different locations where channel info might be stored
        locations = [
            # Location 1: c4TabbedHeaderRenderer
            lambda: (
                json_data.get("header", {})
                .get("c4TabbedHeaderRenderer", {})
            ),
            # Location 2: metadata
            lambda: (
                json_data.get("metadata", {})
                .get("channelMetadataRenderer", {})
            ),
            # Location 3: microformat
            lambda: (
                json_data.get("microformat", {})
                .get("microformatDataRenderer", {})
            ),
            # Location 4: sidebar
            lambda: (
                json_data.get("sidebar", {})
                .get("channelSidebarRenderer", {})
                .get("items", [{}])[0]
                .get("channelAboutFullMetadataRenderer", {})
            )
        ]

        for get_location in locations:
            data = get_location()
            channel_id = data.get("channelId") or data.get("externalId")
            if channel_id:
                channel_title = (
                    data.get("title") or 
                    data.get("simpleText") or 
                    data.get("title", {}).get("simpleText", "Unknown")
                )
                return channel_id, channel_title

        return None, "Unknown"

    @staticmethod
    def extract_avatar_url(json_data: dict) -> Optional[str]:
        """Extract avatar URL from various locations in the JSON."""
        # Check multiple possible locations for avatar
        avatar_locations = [
            # Location 1: c4TabbedHeaderRenderer
            lambda: (
                json_data.get("header", {})
                .get("c4TabbedHeaderRenderer", {})
                .get("avatar", {})
                .get("thumbnails", [{}])[-1]
                .get("url")
            ),
            # Location 2: metadata
            lambda: (
                json_data.get("metadata", {})
                .get("channelMetadataRenderer", {})
                .get("avatar", {})
                .get("thumbnails", [{}])[-1]
                .get("url")
            ),
            # Location 3: decoratedAvatarViewModel
            lambda: (
                json_data.get("decoratedAvatarViewModel", {})
                .get("avatar", {})
                .get("avatarViewModel", {})
                .get("image", {})
                .get("sources", [{}])[-1]
                .get("url")
            ),
            # Location 4: sidebar
            lambda: (
                json_data.get("sidebar", {})
                .get("channelSidebarRenderer", {})
                .get("items", [{}])[0]
                .get("channelAboutFullMetadataRenderer", {})
                .get("avatar", {})
                .get("thumbnails", [{}])[-1]
                .get("url")
            )
        ]

        for get_avatar in avatar_locations:
            avatar_url = get_avatar()
            if avatar_url:
                # Convert relative URLs to absolute
                if avatar_url.startswith('//'):
                    return f"https:{avatar_url}"
                elif avatar_url.startswith('/'):
                    return f"https://www.youtube.com{avatar_url}"
                return avatar_url

        return None

    @staticmethod
    def is_rss_feed(entry: str) -> bool:
        return "feeds/videos.xml?channel_id=" in entry

    @staticmethod
    async def process_rss_feed(entry: str) -> Dict[str, str]:
        channel_id = YouTubeChannel.get_channel_id_from_rss(entry)
        feed_data = feedparser.parse(entry)
        title = feed_data.feed.get("title", "Unknown") if feed_data and feed_data.feed else "Unknown"
        avatar_url = feed_data.feed.get('icon', None)

        if channel_id:
            return {
                "channel_id": channel_id,
                "feed_url": entry,
                "channel_title": title,
                "avatar_url": avatar_url,
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
        entry = 'DistroTube'
        result = await YouTubeChannel.get_channel_info(entry)

        if 'error' in result:
            logger.error(f"❌ Error: {result['error']}")
        else:
            logger.info("✅ Success!")
            logger.info(f"Channel ID    : {result['channel_id']}")
            logger.info(f"Channel Title : {result['channel_title']}")
            logger.info(f"Feed URL      : {result['feed_url']}")
            logger.info(f"Avatar URL    : {result.get('avatar_url')}")
            logger.info(f"Source        : {result['source']}")

    asyncio.run(main())