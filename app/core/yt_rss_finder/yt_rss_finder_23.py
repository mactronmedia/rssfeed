import aiohttp
import asyncio
import logging
import random
import os
import re
import feedparser
from aiohttp import ClientSession
from lxml import html as lxml_html
from selectolax.parser import HTMLParser
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from environment variables (default values provided)
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
USER_AGENTS = os.getenv('USER_AGENTS', "").split(",") or [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Global headers with a random user-agent
headers = {"User-Agent": random.choice(USER_AGENTS)}

class Database:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['video_database']
    collection_feeds = db['feeds']
    collection_videos = db['videos']

    @staticmethod
    async def feed_exists(feed_url):
        doc = await Database.collection_feeds.find_one({'feed': feed_url})
        return doc is not None

    @staticmethod
    async def video_exists(video_id):
        doc = await Database.collection_videos.find_one({'video_id': video_id})
        return doc is not None

    @staticmethod
    async def bulk_insert_videos(video_data_list):
        if video_data_list:
            result = await Database.collection_videos.insert_many(video_data_list)
            logging.info(f"Inserted {len(result.inserted_ids)} videos.")
            return result.inserted_ids
        return []

class YouTubeChannel:
    @staticmethod
    async def get_channel_info(entry: str, session: ClientSession) -> dict:
        """Retrieve channel info from a given entry (either URL or channel name)."""
        entry = YouTubeChannel.normalize_entry(entry)

        if YouTubeChannel.is_rss_feed(entry):
            return await YouTubeChannel.process_rss_feed(entry, session)

        html = await YouTubeChannel.fetch_page(entry, session)
        if not html:
            return {"error": "Failed to retrieve channel page."}

        feed_url = YouTubeChannel.extract_feed_url(html)

        if feed_url:
            await YouTubeParser.channel_data(feed_url, session)
        else:
            return {"error": "RSS feed link not found on the channel page."}

        channel_id = YouTubeChannel.get_channel_id_from_rss(feed_url)
        if not channel_id:
            return {"error": "Channel ID not found in the RSS feed URL."}

        return {"channel_id": channel_id, "feed_url": feed_url, "source": "html_parsed"}

    @staticmethod
    def is_rss_feed(entry: str) -> bool:
        """Check if the entry is a direct YouTube RSS feed URL."""
        return "feeds/videos.xml?channel_id=" in entry

    @staticmethod
    async def process_rss_feed(entry: str, session: ClientSession) -> dict:
        """Process a direct RSS feed entry."""
        channel_id = YouTubeChannel.get_channel_id_from_rss(entry)
        if channel_id:
            await YouTubeParser.channel_data(entry, session)
            return {"channel_id": channel_id, "feed_url": entry, "source": "direct_rss"}
        
        return {"error": f"Channel ID not found in the RSS feed URL: {entry}. Please ensure it's a valid YouTube RSS feed."}

    @staticmethod
    def normalize_entry(entry: str) -> str:
        """Normalize user input into a full YouTube URL."""
        if entry.startswith('@'):
            return f"https://www.youtube.com/{entry}"
        if entry.startswith(('/user/', '/c/', '/channel/')):
            return f"https://www.youtube.com{entry}"
        if not entry.startswith('http'):
            return f"https://www.youtube.com/{entry}"
        return entry

    @staticmethod
    async def fetch_page(url: str, session: ClientSession) -> str:
        """Fetch page content, handling consent form if needed."""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()

                # Check if we need to handle consent
                if 'itemprop' not in html and 'consent.youtube.com' in html:
                    return await YouTubeChannel.handle_consent(session, html)

                return html
        except Exception as e:
            logging.error(f"Error fetching page: {e}")
            return None

    @staticmethod
    async def handle_consent(session: ClientSession, html: str) -> str:
        """Handle YouTube consent form using selectolax."""
        try:
            parser = HTMLParser(html)
            form = parser.css_first('form')
            if not form:
                return None
                
            post_url = form.attributes.get('action')
            if not post_url:
                return None
                
            # Build form data
            form_data = {}
            for input_tag in form.css('input'):
                name = input_tag.attributes.get('name')
                if name:
                    form_data[name] = input_tag.attributes.get('value', '')
            
            # Submit consent form
            async with session.post(post_url, data=form_data) as response:
                if response.status == 200:
                    return await response.text()
                return None
        except Exception as e:
            logging.error(f"Error handling consent: {e}")
            return None

    @staticmethod
    def extract_feed_url(html: str) -> str:
        """Extract RSS feed URL from the HTML content."""
        try:
            tree = lxml_html.fromstring(html)
            rss_link = tree.xpath('//link[@rel="alternate" and @type="application/rss+xml"]')
            return rss_link[0].attrib['href'] if rss_link else None
        except Exception as e:
            logging.error(f"Error extracting feed URL: {e}")
            return None

    @staticmethod
    def get_channel_id_from_rss(feed_url: str) -> str:
        """Extract channel ID from the RSS feed URL."""
        try:
            match = re.search(r'channel_id=([A-Za-z0-9_-]+)', feed_url)
            if match:
                channel_id = match.group(1)
                return channel_id
            return None
        except Exception as e:
            logging.error(f"Error extracting channel ID: {e}")
            return None

class YouTubeParser:
    @staticmethod
    async def channel_data(feed_url: str, session: ClientSession):
        feed = feedparser.parse(feed_url)
        feed_type = "video"
        language = 'en'

        if await Database.feed_exists(feed_url):
            logging.info(f"Feed {feed_url} already exists. Skipping feed save.")
            feed_object_id = None
        else:
            channel_id = "UC" + feed.feed.get('yt_channelid', '')
            channel_name = feed.feed.get('title')
            channel_description = feed.feed.get('description', '')

            feed_data = {
                'name': channel_name,
                'description': channel_description,
                'type': feed_type,
                'feed': feed_url,
            }

            result = await Database.collection_feeds.insert_one(feed_data)
            feed_object_id = result.inserted_id
            logging.info(f"Inserted feed with id: {feed_object_id}")

        await YouTubeParser.video_items(feed, session, feed_object_id)

    @staticmethod
    async def video_items(feed, session: ClientSession, feed_object_id):
        video_data_list = []
        for entry in feed.entries:
            video_id = entry.get('yt_videoid') or entry.get('yt:videoId')
            video_title = entry.get('title', 'No Title')
            video_description = entry.get('description', None)
            video_published = entry.get('published', 'N/A')
            channel_id = entry.get('yt_channelid', None)

            video_thumbnail = (
                entry.get('media_thumbnail', [{}])[0].get('url') or
                entry.get('media_content', [{}])[0].get('url') or
                entry.get('image', None)
            )

            video_data = {
                'feed_id': feed_object_id,
                'video_id': video_id,
                'channel_id': channel_id,
                'title': video_title,
                'description': video_description,
                'published': video_published,
                'thumbnail': video_thumbnail,
            }

            if await Database.video_exists(video_id):
                logging.info(f"Video {video_id} already exists. Skipping.")
                continue

            video_data_list.append(video_data)

        # Bulk insert videos
        if video_data_list:
            await Database.bulk_insert_videos(video_data_list)

async def main():
    # Create a single session that can be used throughout
    async with aiohttp.ClientSession(headers=headers) as session:
        entry = 'BBC'
        result = await YouTubeChannel.get_channel_info(entry, session)

        if 'error' in result:
            logging.error(f"❌ Error: {result['error']}")
        else:
            logging.info("✅ Success!")
            logging.info(f"Channel ID : {result['channel_id']}")
            logging.info(f"Feed URL   : {result['feed_url']}")
            logging.info(f"Source     : {result['source']}")

# Run the asyncio loop
asyncio.run(main())
