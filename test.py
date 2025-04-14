import feedparser

# YouTube RSS feed URL for a specific channel
feed_url = "https://www.youtube.com/feeds/videos.xml?channel_id=UC-yVJTkW_Hz8_1vtcFtbSHQ"  # Example: Google Developers Channel

# Parse the feed
feed = feedparser.parse(feed_url)

# Check if feed was parsed successfully
if feed.get("bozo", 0):
    print("Error parsing feed:", feed.bozo_exception)
else:
    print(f"Feed Title: {feed.feed.title}")
    print(f"Feed Link: {feed.feed.link}")
    
    # Loop through entries (videos)
    for entry in feed.entries:
        print(f"\nVideo Title: {entry.title}")
        print(f"Video Link: {entry.link}")
        print(f"Published: {entry.published}")
        print(f"Summary: {entry.summary}")
