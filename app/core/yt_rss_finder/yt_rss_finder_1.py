import re
import requests
from selectolax.parser import HTMLParser

class YouTubeChannel:
    @staticmethod
    def get_channel_id(entry: str) -> str:
        entry = YouTubeChannel.normalize_entry(entry)
        response = YouTubeChannel.fetch_page(entry)
        
        if response.status_code == 200:
            html = response.text
            rss_url = YouTubeChannel.extract_rss_url(html)
            
            if rss_url:
                channel_id = YouTubeChannel.get_channel_id_from_rss(rss_url)
                return channel_id if channel_id else "No channel_id found in the RSS feed URL."
            else:
                return "RSS Feed link not found."
        else:
            return f"Failed to retrieve channel page. Status code: {response.status_code}"

    @staticmethod
    def normalize_entry(entry: str) -> str:
        """Normalize entry to a full URL if it's a handle."""
        if entry.startswith('@'):
            return f"https://www.youtube.com/{entry}"
        return entry

    @staticmethod
    def fetch_page(url: str) -> requests.Response:
        """Send a GET request to fetch the page content."""
        return requests.get(url)

    @staticmethod
    def extract_rss_url(html: str) -> str:
        """Extract RSS URL from the HTML content."""
        tree = HTMLParser(html)
        rss_link = tree.css_first('link[rel="alternate"][type="application/rss+xml"]')
        return rss_link.attributes['href'] if rss_link else None

    @staticmethod
    def get_channel_id_from_rss(rss_url: str) -> str:
        """Extract channel ID from the RSS URL."""
        match = re.search(r'channel_id=([A-Za-z0-9_-]+)', rss_url)
        return match.group(1) if match else None


if __name__ == "__main__":
    # Test with a full URL
    entry = 'https://youtube.com/channel/UCvFGlf1nQNHHUxKhprE7KSQ'
    channel_id = YouTubeChannel.get_channel_id(entry)
    print(f"Channel ID from full URL: {channel_id}")

    # Test with a handle
    entry = '@Google'
    channel_id = YouTubeChannel.get_channel_id(entry)
    print(f"Channel ID from handle: {channel_id}")
