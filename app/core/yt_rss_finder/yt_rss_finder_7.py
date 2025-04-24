import aiohttp
import re
from bs4 import BeautifulSoup
from aiohttp import ClientSession
from async_timeout import timeout
from lxml import html as HTMLParser

UA = (
    "Mozilla/5.0 (Linux; cli) pyrequests/0.1 "
    "(python, like Gecko, like KHTML, like wget, like CURL) myscrapper/1.0"
)
headers = {"User-Agent": UA}

class YouTubeChannel:
    @staticmethod
    async def get_channel_info(entry: str) -> dict:
        """Retrieve channel info from a given entry (either URL or channel name)."""
        entry = YouTubeChannel.normalize_entry(entry)

        if YouTubeChannel.is_rss_feed(entry):
            return await YouTubeChannel.process_rss_feed(entry)

        html = await YouTubeChannel.fetch_page(entry)
        if not html:
            return {"error": "Failed to retrieve channel page."}

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
    async def process_rss_feed(entry: str) -> dict:
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
    async def fetch_page(url: str) -> str:
        """Fetch page content, handling consent form if needed."""
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    html = await response.text()
                    
                    # Check if we need to handle consent
                    if 'itemprop' not in html and 'consent.youtube.com' in html:
                        return await YouTubeChannel.handle_consent(session, html)
                    
                    return html
        except Exception as e:
            print(f"Error fetching page: {e}")
            return None

    @staticmethod
    async def handle_consent(session: ClientSession, html: str) -> str:
        """Handle YouTube consent form."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            form = soup.find('form')
            if not form:
                return None
                
            post_url = form.get('action')
            if not post_url:
                return None
                
            # Build form data
            form_data = {}
            for input_tag in form.find_all('input'):
                if input_tag.get('name'):
                    form_data[input_tag['name']] = input_tag.get('value', '')
            
            # Submit consent form
            async with session.post(post_url, data=form_data) as response:
                if response.status == 200:
                    return await response.text()
                return None
        except Exception as e:
            print(f"Error handling consent: {e}")
            return None

    @staticmethod
    def extract_feed_url(html: str) -> str:
        """Extract RSS feed URL from the HTML content."""
        try:
            tree = HTMLParser.fromstring(html)
            rss_link = tree.xpath('//link[@rel="alternate" and @type="application/rss+xml"]')
            return rss_link[0].attrib['href'] if rss_link else None
        except Exception as e:
            print(f"Error extracting feed URL: {e}")
            return None

    @staticmethod
    def get_channel_id_from_rss(feed_url: str) -> str:
        """Extract channel ID from the RSS feed URL."""
        try:
            match = re.search(r'channel_id=([A-Za-z0-9_-]+)', feed_url)
            if match:
                channel_id = match.group(1)
                YouTubeChannel.finalize(channel_id, feed_url)
                return channel_id
            return None
        except Exception as e:
            print(f"Error extracting channel ID: {e}")
            return None

    @staticmethod
    def finalize(channel_id: str, feed_url: str):
        """Log the extracted channel ID and feed URL."""
        print(f"Channel ID: {channel_id}")
        print(f"Feed URL: {feed_url}")
        print("Extraction successful!")


if __name__ == "__main__":
    import asyncio

    async def main():
        # Example usage
        entry = '@DistroTube'
        result = await YouTubeChannel.get_channel_info(entry)

        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print("✅ Success!")
            print(f"Channel ID : {result['channel_id']}")
            print(f"Feed URL   : {result['feed_url']}")
            print(f"Source     : {result['source']}")

    asyncio.run(main())