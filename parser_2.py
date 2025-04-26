import asyncio
import aiohttp
import atoma

# Asynchronous function to fetch and parse the RSS feed
async def fetch_tmz_feed():
    rss_url = "https://www.tmz.com/rss.xml"
    
    async with aiohttp.ClientSession() as session:
        # Fetch the RSS feed asynchronously
        async with session.get(rss_url) as response:
            response_content = await response.read()

            # Parse the feed with atoma
            feed = atoma.parse_rss_bytes(response_content)
            
            # Print the feed title
            print(f"Feed Title: {feed.title}")
            
            # Loop through the entries and print details
            for entry in feed.items:
                print(f"Title: {entry.title}")
                print(f"Link: {entry.link}")
                print(f"Published: {entry.pub_date}")
                print("-" * 60)

# Run the async function
if __name__ == "__main__":
    asyncio.run(fetch_tmz_feed())
