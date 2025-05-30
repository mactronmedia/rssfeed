import requests
import feedparser
 

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
    def process_video_feed(feed_url, feed_type):
        print(f"Fetching video from: {feed_url} (type: {feed_type})")

    @staticmethod
    def channel_metadata(feed_url, feed_type):
        feed_type = feed_type
        channel_name = feed.feed.get('title')
        channel_link = feed.feed.get('link')
        channel_id = feed.feed.get('yt_channelid')
        channel_id = "UC" + feed.feed.get('yt_channelid', '') # UC = Unique Channel

        print(feed_type)
        print(channel_name)
        print(channel_link)
        print(channel_id)

        if channel_name:
            VideosModule.video_items(feed_url)


    @staticmethod
    def video_items(feed_url):
        for entry in feed.entries[:5]:  # Limit to 5 entries
            video_title = entry.get('title', 'No Title')
            video_description = entry.get('description', 'No Description')
            video_published = entry.get('published', 'N/A')

            thumbnail = (
                entry.get('media_thumbnail', [{}])[0].get('url') or
                entry.get('media_content', [{}])[0].get('url') or
                entry.get('image', None)
            )

            print("Thumbnail:", thumbnail)
            print(f'Title: {video_title}')
            #print(f'Description: {video_description}' )
            print(f'Published: {video_published}')
            print(thumbnail)

            channel_thubnail =  VideosModule.parse_channel_image(thumbnail)


    @staticmethod
    def parse_channel_image(feed_url):
        """
        Fetch the feed page and parse the image URL using Selectolax.
        """
        try:
            response = requests.get(feed_url)
            if response.status_code == 200:
                tree = HTMLParser(response.text)
                image = tree.css_first('img#img')  # Use CSS selector to find the image by its ID
                
                if image:
                    image_url = image.attributes.get('src')
                    if image_url:
                        print(f"Channel Image URL: {image_url}")
                    else:
                        print("Image URL not found.")
                else:
                    print("No image with the specified ID found.")
            else:
                print(f"Failed to fetch feed page, status code: {response.status_code}")
        except Exception as e:
            print(f"Error fetching or parsing feed: {e}")




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
    feed_url = 'https://www.youtube.com/feeds/videos.xml?channel_id=UC2pXuIvKlD464_H5Yssu5bQ'
    feed = feedparser.parse(feed_url)
    feed_type = FeedProcessor.get_feed_type(feed, feed_url)