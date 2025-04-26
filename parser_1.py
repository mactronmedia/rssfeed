import asyncio
import aiohttp
import feedparser

async def fetch_tmz_feed():
    url = "https://www.tmz.com/rss.xml"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content = await response.text()
            feed = feedparser.parse(content)
            
            print(f"Feed Title: {feed.feed.title}\n")
            
            for entry in feed.entries:
                print(f"Title: {entry.title}")
                print(f"Link: {entry.link}")
                #print(f"Published: {entry.published}")
                print("-" * 60)

if __name__ == "__main__":
    asyncio.run(fetch_tmz_feed())
