import re
import requests
from selectolax.parser import HTMLParser


class YouTubeChannel:
    @staticmethod
    def get_channel_info(entry: str) -> dict:
        """Retrieve channel info from a given entry (either URL or channel name)."""
        entry = YouTubeChannel.normalize_entry(entry)

        if YouTubeChannel.is_rss_feed(entry):
            return YouTubeChannel.process_rss_feed(entry)

        response = YouTubeChannel.fetch_page(entry)
        if response.status_code != 200:
            return {"error": f"Failed to retrieve channel page. Status code: {response.status_code}"}

        html = response.text
        feed_url = YouTubeChannel.extract_feed_url(html)

        if not feed_url:
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
    def process_rss_feed(entry: str) -> dict:
        """Process a direct RSS feed entry."""
        channel_id = YouTubeChannel.get_channel_id_from_rss(entry)
        if channel_id:
            return {"channel_id": channel_id, "feed_url": entry, "source": "direct_rss"}
        return {"error": "Invalid RSS feed URL format."} 

    @staticmethod
    def normalize_entry(entry: str) -> str:
        """Normalize user input into a full YouTube URL."""
        if entry.startswith('@'):
            return f"https://www.youtube.com/{entry}"
        if entry.startswith(('/user/', '/c/')):
            return f"https://www.youtube.com{entry}"
        if not entry.startswith('http'):
            return f"https://www.youtube.com/{entry}"
        return entry

    @staticmethod
    def fetch_page(url: str) -> requests.Response:
        """Send a GET request to fetch the page content."""
        return requests.get(url)

    @staticmethod
    def extract_feed_url(html: str) -> str:
        """Extract RSS feed URL from the HTML content."""
        tree = HTMLParser(html)
        rss_link = tree.css_first('link[rel="alternate"][type="application/rss+xml"]')
        return rss_link.attributes['href'] if rss_link else None

    @staticmethod
    def get_channel_id_from_rss(feed_url: str) -> str:
        """Extract channel ID from the RSS feed URL."""
        match = re.search(r'channel_id=([A-Za-z0-9_-]+)', feed_url)
        if match:
            channel_id = match.group(1)
            YouTubeChannel.finalize(channel_id, feed_url)  # Finalize extraction
            return channel_id
        return None

    @staticmethod
    def finalize(channel_id: str, feed_url: str):
        """Log the extracted channel ID and feed URL."""
        print(f"Channel ID: {channel_id}")
        print(f"Feed URL: {feed_url}")
        print("Extraction successful!")



if __name__ == "__main__":
    # Example usage
    entry = 'https://www.youtube.com/DistroTube'
    result = YouTubeChannel.get_channel_info(entry)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print("✅ Success!")
        print(f"Channel ID : {result['channel_id']}")
        print(f"Feed URL   : {result['feed_url']}")
        print(f"Source     : {result['source']}")
