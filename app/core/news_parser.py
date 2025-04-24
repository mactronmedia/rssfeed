import aiohttp
import asyncio
import feedparser
from typing import Dict, List, Any

class AsyncRSSParser:
    @staticmethod
    async def fetch_feed(session: aiohttp.ClientSession, feed_url: str) -> str:
        async with session.get(feed_url) as response:
            return await response.text()

    @staticmethod
    async def get_feed_info(feed_url: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            feed_content = await AsyncRSSParser.fetch_feed(session, feed_url)
            feed = feedparser.parse(feed_content)
            
            feed_info = {
                'title': feed.feed.get('title', ''),
                'link': feed.feed.get('link', ''),
                'description': feed.feed.get('description', ''),
                'published': feed.feed.get('published', ''),
                'language': feed.feed.get('language', ''),
                'version': feed.version if hasattr(feed, 'version') else ''
            }
            
            return feed_info
    
    @staticmethod
    async def get_feed_entries(feed_url: str) -> List[Dict[str, Any]]:
        """
        Get all entries from the RSS feed asynchronously.
        
        Args:
            feed_url: URL of the RSS feed to parse
            
        Returns:
            List of dictionaries containing entry information
        """
        async with aiohttp.ClientSession() as session:
            feed_content = await AsyncRSSParser.fetch_feed(session, feed_url)
            feed = feedparser.parse(feed_content)
            entries = []
            
            for entry in feed.entries:
                entry_info = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', ''),
                    'author': entry.get('author', ''),
                    'id': entry.get('id', '')
                }
                entries.append(entry_info)
                
            return entries


# Example usage
async def main():
    # Example RSS feed URL (you can replace with any RSS feed)
    test_feed_url = "https://rss.politico.com/congress.xml"
    
    # Get and display feed information
    feed_info = await AsyncRSSParser.get_feed_info(test_feed_url)
    print("Feed Information:")
    for key, value in feed_info.items():
        print(f"{key.capitalize()}: {value}")
    
    print("\nLatest Entries:")
    # Get and display the first 3 entries
    entries = await AsyncRSSParser.get_feed_entries(test_feed_url)
    for i, entry in enumerate(entries[:3], 1):
        print(f"\nEntry {i}:")
        print(f"Title: {entry['title']}")
        print(f"Published: {entry['published']}")
        print(f"Link: {entry['link']}")

if __name__ == "__main__":
    asyncio.run(main())