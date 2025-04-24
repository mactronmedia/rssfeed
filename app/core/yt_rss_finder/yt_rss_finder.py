import re
import requests
from selectolax.parser import HTMLParser

class YouTubeChannel:
    @staticmethod
    def get_channel_id(channel_url: str) -> str:
        # Send a GET request to the channel page
        response = requests.get(channel_url)

        if response.status_code == 200:
            html = response.text
            # Parse the HTML content
            tree = HTMLParser(html)
            
            rss_link = tree.css_first('link[rel="alternate"][type="application/rss+xml"]')
            
            if rss_link:
                rss_url = rss_link.attributes['href']
                match = re.search(r'channel_id=([A-Za-z0-9_-]+)', rss_url)
                if match:
                    return match.group(1)
                else:
                    return "No channel_id found in the RSS feed URL."
            else:
                return "RSS Feed link not found."
        else:
            return f"Failed to retrieve channel page. Status code: {response.status_code}"

if __name__ == "__main__":
    channel_url = 'https://www.youtube.com/channel/UCvFGlf1nQNHHUxKhprE7KSQ'
    channel_id = YouTubeChannel.get_channel_id(channel_url)
    print(f"Channel ID: {channel_id}")
