import os
import aiohttp
import asyncio
import random
import feedparser
from typing import Dict, List, Any
from utilities.helpers import proxy, retry

USER_AGENTS = [ua for ua in os.getenv('USER_AGENTS', "").split(",") if ua.strip()] or [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Global headers with a random user-agent
headers = {"User-Agent": random.choice(USER_AGENTS)}

class AsyncRSSParser:

    @staticmethod
    @proxy
    @retry(retries=3, delay=1, backoff=2, jitter=True)
    async def get_feed_info(session: aiohttp.ClientSession, feed_url: str) -> Dict[str, Any]:
        feed_content = await AsyncRSSParser.fetch_feed(session, feed_url)
        feed = feedparser.parse(feed_content)

        return {
            'title': feed.feed.get('title', ''),
            'link': feed.feed.get('link', ''),
            'description': feed.feed.get('description', ''),
            'published': feed.feed.get('published', ''),
            'language': feed.feed.get('language', ''),
            'version': getattr(feed, 'version', '')
        }


    @staticmethod
    def is_valid_feed(content: str) -> bool:
        """Validate if the content is XML or Atom feed."""
        feed = feedparser.parse(content)
        return not getattr(feed, 'bozo', True)  # bozo=True means parsing failed

    @proxy
    @staticmethod
    async def fetch_feed(session: aiohttp.ClientSession, feed_url: str) -> str:
        async with session.get(feed_url) as response:
            content = await response.text()
            if not AsyncRSSParser.is_valid_feed(content):
                raise ValueError(f"Invalid feed format at {feed_url}. Must be XML or Atom.")
            return content

    @staticmethod
    async def get_feed_entries(session: aiohttp.ClientSession, feed_url: str) -> List[Dict[str, Any]]:
        feed_content = await AsyncRSSParser.fetch_feed(session, feed_url)
        feed = feedparser.parse(feed_content)
        entries = []

        for entry in feed.entries:
            entries.append({
                'title': entry.get('title', ''),
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'summary': entry.get('summary', ''),
                'author': entry.get('author', ''),
                'id': entry.get('id', '')
            })

        return entries


# Example usage
async def main():
    async with aiohttp.ClientSession(headers=headers) as session:
        entry = "https://feeds.feedburner.com/ekathimerini/sKip"

        try:
            feed_info = await AsyncRSSParser.get_feed_info(session, entry)
            print("Feed Information:")
            for key, value in feed_info.items():
                print(f"{key.capitalize()}: {value}")

            print("\nLatest Entries:")
            entries = await AsyncRSSParser.get_feed_entries(session, entry)
            for i, entry in enumerate(entries):
                print(f"\nEntry {i}:")
                print(f"Title: {entry['title']}")
                print(f"Published: {entry['published']}")
                print(f"Link: {entry['link']}")
        except ValueError as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())