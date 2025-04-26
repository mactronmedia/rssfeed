import time
import requests
import feedparser
import atoma
import aiohttp
import asyncio

# URL for the RSS feed
rss_url = "https://www.france24.com/es/rss"

# Function to measure feedparser speed and print 10 titles
def measure_feedparser():
    start_time = time.time()

    response = requests.get(rss_url)
    feed = feedparser.parse(response.content)

    # Extract and print the first 10 titles
    print("Feedparser Titles:")
    for entry in feed.entries[:10]:
        print(entry.title)

    elapsed_time = time.time() - start_time
    print(f"\nFeedparser: {elapsed_time:.4f} seconds")
    return elapsed_time

# Function to measure atoma speed and print 10 titles
def measure_atoma():
    start_time = time.time()

    response = requests.get(rss_url)
    feed = atoma.parse_rss_bytes(response.content)

    # Extract and print the first 10 titles (Accessing items in Atoma's RSSChannel)
    print("Atoma Titles:")
    for entry in feed.items[:10]:
        print(entry.title)

    elapsed_time = time.time() - start_time
    print(f"\nAtoma: {elapsed_time:.4f} seconds")
    return elapsed_time

# Function to measure fastfeed (async) speed and print 10 titles
async def measure_fastfeed():
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        async with session.get(rss_url) as response:
            content = await response.read()
            feed = feedparser.parse(content)

            # Extract and print the first 10 titles
            print("Fastfeed (Async) Titles:")
            for entry in feed.entries[:10]:
                print(entry.title)

            elapsed_time = time.time() - start_time
            print(f"\nFastfeed (Async): {elapsed_time:.4f} seconds")
            return elapsed_time

# Main function to run all tests
async def main():
    print("Starting RSS Feed Parsing Speed Test...\n")

    # Measure Feedparser (synchronous)
    feedparser_time = measure_feedparser()

    # Measure Atoma (synchronous)
    atoma_time = measure_atoma()

    # Measure Fastfeed (asynchronous) - Ensure we await the coroutine here
    fastfeed_time = await measure_fastfeed()

    # You can also compare times if needed:
    print(f"\nComparison Results (time taken in seconds):")
    print(f"Feedparser: {feedparser_time:.4f} seconds")
    print(f"Atoma: {atoma_time:.4f} seconds")
    print(f"Fastfeed: {fastfeed_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
