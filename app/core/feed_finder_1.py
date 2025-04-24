import warnings
from feed_seeker import find_feed_url
from bs4 import XMLParsedAsHTMLWarning

# Suppress the XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

url = 'https://open.spotify.com/show/3a7VVZmGQMlneZHHh3F5Ca'

try:
    feed_url = find_feed_url(url)
    if feed_url:
        print(f"Feed URL found: {feed_url}")
    else:
        print("No feed URL found.")
except Exception as e:
    print(f"An error occurred: {e}")
