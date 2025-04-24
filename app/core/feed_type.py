import feedparser

def get_feed_type(feed_url):
    feed = feedparser.parse(feed_url)

    is_youtube = False
    is_podcast = False

    # Check for YouTube or podcast namespaces
    namespaces = feed.get('namespaces', {})
    if 'yt' in namespaces: is_youtube = True
    if 'itunes' in namespaces: is_podcast = True

    # Check entries for YouTube or podcast-specific elements
    for entry in feed.entries:
        if 'yt_videoid' in entry:
            is_youtube = True
        if 'enclosures' in entry or 'enclosure' in entry:
            is_podcast = True

    # Determine feed type
    if is_youtube:
        process_video_feed(feed_url, "video")  # pass correct string
        return "video"
    elif is_podcast:
        process_podcast_feed(feed_url, "podcast")  # pass correct string
        return "podcast"
    else:
        return "news"
        process_news_feed(feed_url, "news")  # pass correct string

def process_video_feed(feed_url, feed_type):
    print(f"Fetching video from: {feed_url} (type: {feed_type})")

def process_podcast_feed(feed_url, feed_type):
    print(f"Fetching video from: {feed_url} (type: {feed_type})")

def process_news_feed(feed_url, feed_type):
    print(f"Fetching video from: {feed_url} (type: {feed_type})")

# Example usage:
feed_url = 'https://feeds.bbci.co.uk/news/rss.xml'
feed_type = get_feed_type(feed_url)
print(feed_type)
