import asyncio
import aiohttp
import feedparser
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId


class Database:
    client = AsyncIOMotorClient('mongodb://localhost:27017/')
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


class FeedProcessor:
    @staticmethod
    async def fetch_feed(feed_url):
        async with aiohttp.ClientSession() as session:
            async with session.get(feed_url) as response:
                content = await response.read()
                return feedparser.parse(content)

    @staticmethod
    async def get_feed_type(feed, feed_url):
        is_youtube = 'yt' in feed.get('namespaces', {})
        is_podcast = 'itunes' in feed.get('namespaces', {})

        for entry in feed.entries:
            if 'yt_videoid' in entry or 'yt:videoId' in entry:
                is_youtube = True
            if 'enclosure' in entry:
                enclosure = entry['enclosure']
                media_type = enclosure.get('type', '')
                if media_type.startswith('audio/') or media_type.startswith('video/'):
                    is_podcast = True

        if is_youtube:
            feed_type = "video"
            await VideosModule.channel_metadata(feed_url, feed_type, feed)
            return "video"
        elif is_podcast:
            await PodcastsModule.process_podcast_feed(feed_url, "podcast")
            return "podcast"
        else:
            await NewsModule.process_news_feed(feed_url, "news")
            return "news"


class VideosModule:
    @staticmethod
    async def channel_metadata(feed_url, feed_type, feed):
        if await Database.feed_exists(feed_url):
            print(f"Feed {feed_url} already exists. Skipping feed save.")
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
            print(f"Inserted feed with id: {feed_object_id}")

        await VideosModule.video_items(feed, feed_object_id)

    @staticmethod
    async def video_items(feed, feed_object_id):
        for entry in feed.entries:
            video_id = entry.get('yt_videoid') or entry.get('yt:videoId')
            video_title = entry.get('title', 'No Title')
            video_description = entry.get('description', 'No Description')
            video_published = entry.get('published', 'N/A')
            channel_id = entry.get('yt:channelId')

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
                print(f"Video {video_id} already exists. Skipping.")
                continue

            result = await Database.collection_videos.insert_one(video_data)
            print(f"Inserted video {video_id} with ID: {result.inserted_id}")


class NewsModule:
    @staticmethod
    async def process_news_feed(feed_url, feed_type):
        print(f"Fetching news from: {feed_url} (type: {feed_type})")

class PodcastsModule:
    @staticmethod
    async def process_podcast_feed(feed_url, feed_type):
        print(f"Fetching podcast from: {feed_url} (type: {feed_type})")

async def main():
    feed_url = 'https://www.youtube.com/@LinusTechTips'
    feed = await FeedProcessor.fetch_feed(feed_url)
    await FeedProcessor.get_feed_type(feed, feed_url)


if __name__ == "__main__":
    asyncio.run(main())
