import feedparser
from pymongo import MongoClient
from bson.objectid import ObjectId


class Database:
    client = MongoClient('mongodb://localhost:27017/')  # Connect to MongoDB on localhost
    db = client['video_database']  # Use a database named "video_database"
    collection_feeds = db['feeds']  # Use a collection named "feeds"
    collection_videos = db['videos']  # Use a collection named "videos"

    @staticmethod
    def feed_exists(feed_url):
        return Database.collection_feeds.find_one({'feed': feed_url}) is not None

    @staticmethod
    def video_exists(video_id):
        return Database.collection_videos.find_one({'video_id': video_id}) is not None


class FeedProcessor:
    @staticmethod
    def get_feed_type(feed, feed_url):
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
            VideosModule.channel_metadata(feed_url, feed_type)
            return "video"
        elif is_podcast:
            PodcastsModule.process_podcast_feed(feed_url, "podcast")
            return "podcast"
        else:
            NewsModule.process_news_feed(feed_url, "news")
            return "news"


class VideosModule:
    @staticmethod
    def channel_metadata(feed_url, feed_type):
        # Check if feed exists
        if Database.feed_exists(feed_url):
            print(f"Feed {feed_url} already exists. Skipping feed save and processing videos.")
        else:
            # Feed does not exist, so we proceed to save feed data
            channel_id = "UC" + feed.feed.get('yt_channelid', '')  # UC = Unique Channel
            channel_name = feed.feed.get('title')
            channel_link = feed.feed.get('link')
            channel_description = feed.feed.get('description', '') or ''  # fallback to empty string

            feed_data = {
                'name': channel_name,
                'description': channel_description,
                'type': feed_type,
                'feed': feed_url,
            }

            result = Database.collection_feeds.insert_one(feed_data)
            feed_object_id = result.inserted_id
            print(f"Inserted feed with id: {feed_object_id}")

        # Regardless of whether the feed exists, we process the videos
        VideosModule.video_items(feed_url, None)

    @staticmethod
    def video_items(feed_url, feed_object_id):
        for entry in feed.entries:
            video_id = entry.get('yt_videoid')
            video_link = entry.get('link')
            video_title = entry.get('title', 'No Title')
            video_description = entry.get('description', 'No Description')
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

            if Database.video_exists(video_id):
                print(f"Video {video_id} already exists. Skipping.")
                continue  # Skip duplicates

            result = Database.collection_videos.insert_one(video_data)
            print(f"Inserted video {video_id} with ID: {result.inserted_id}")

class NewsModule:
    @staticmethod
    def process_news_feed(feed_url, feed_type):
        print(f"Fetching news from: {feed_url} (type: {feed_type})")

class PodcastsModule:
    @staticmethod
    def process_podcast_feed(feed_url, feed_type):
        print(f"Fetching podcast from: {feed_url} (type: {feed_type})")


# Example usage
if __name__ == "__main__":
    feed_url = 'https://www.youtube.com/feeds/videos.xml?channel_id=UCUyeluBRhGPCW4rPe_UvBZQ'
    feed = feedparser.parse(feed_url)
    feed_type = FeedProcessor.get_feed_type(feed, feed_url)