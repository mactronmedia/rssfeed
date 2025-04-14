import feedparser

# RSS feed URL for GeekWire
feed_url = "https://www.geekwire.com/feed/"

# Parse the feed
feed = feedparser.parse(feed_url)

# Display the feed title
print(f"Feed Title: {feed.feed.title}")
print(f"Feed Link: {feed.feed.link}")
print("\nLatest Articles:\n")

# Display the latest 5 articles
for entry in feed.entries[:5]:
    print(f"Title: {entry.title}")
    print(f"Link: {entry.link}")
    print(f"Published: {entry.published}")
    print(f"Summary: {entry.summary}\n")
