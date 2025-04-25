import asyncio
from bs4 import BeautifulSoup
import aiohttp
from urllib.parse import urlparse, parse_qs

async def fetch_youtube_rss(channel_url, session=None):
    """
    Fetch the RSS feed URL from a YouTube channel page.
    
    Args:
        channel_url (str): URL of the YouTube channel
        session (aiohttp.ClientSession): Optional existing session
    
    Returns:
        str: RSS feed URL if found, None otherwise
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    close_session = False
    if session is None:
        session = aiohttp.ClientSession(headers=headers)
        close_session = True
    
    try:
        # Ensure URL starts with https://
        if not channel_url.startswith('http'):
            channel_url = f'https://{channel_url}'
            
        # Handle different YouTube URL formats
        if 'youtube.com/@' in channel_url:
            # Handle @username format
            pass
        elif 'youtube.com/c/' in channel_url:
            # Handle /c/ format
            pass
        elif 'youtube.com/user/' in channel_url:
            # Handle /user/ format
            pass
        elif 'youtube.com/channel/' in channel_url:
            # Direct channel ID URL - we can construct RSS directly
            channel_id = channel_url.split('/channel/')[-1].split('/')[0]
            if channel_id.startswith('UC') and len(channel_id) == 24:
                rss_url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
                return rss_url
        
        async with session.get(channel_url) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Method 1: Look for RSS link tag
                rss_link = soup.find('link', {
                    'rel': 'alternate',
                    'type': 'application/rss+xml',
                    'title': 'RSS'
                })
                
                if rss_link:
                    return rss_link.get('href')
                
                # Method 2: Try to find channel ID in metadata
                meta_tag = soup.find('meta', {'itemprop': 'channelId'})
                if meta_tag:
                    channel_id = meta_tag.get('content')
                    if channel_id.startswith('UC') and len(channel_id) == 24:
                        return f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
                
                # Method 3: Try to find in canonical link
                canonical_link = soup.find('link', {'rel': 'canonical'})
                if canonical_link:
                    href = canonical_link.get('href', '')
                    if '/channel/' in href:
                        channel_id = href.split('/channel/')[-1].split('/')[0]
                        if channel_id.startswith('UC') and len(channel_id) == 24:
                            return f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
                
                print("RSS feed link not found in the page.")
                return None
            else:
                print(f"Failed to fetch page. Status code: {response.status}")
                return None
                
    except Exception as e:
        print(f"An error occurred while processing {channel_url}: {str(e)}")
        return None
    finally:
        if close_session and not session.closed:
            await session.close()

async def process_multiple_channels(channel_urls):
    """
    Process multiple YouTube channels to extract their RSS feeds.
    
    Args:
        channel_urls (list): List of YouTube channel URLs
        
    Returns:
        dict: Dictionary mapping channel URLs to their RSS feeds
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for url in channel_urls:
            tasks.append(fetch_youtube_rss(url, session))
        
        results = await asyncio.gather(*tasks)
        
        return {url: rss for url, rss in zip(channel_urls, results)}

async def main():
    # Single channel example
    print("Fetching RSS feed for single channel:")
    channel_url = "https://www.youtube.com/DistroTube"
    rss_url = await fetch_youtube_rss(channel_url)
    if rss_url:
        print(f"Found RSS feed URL: {rss_url}")
    else:
        print("Could not find RSS feed URL.")
    
    # Multiple channels example
    print("\nFetching RSS feeds for multiple channels:")
    channels = [
        "https://www.youtube.com/@Mihilizem",
        "https://www.youtube.com/@LinusTechTips",
        "https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw",  # Linus Tech Tips channel ID
        "https://www.youtube.com/c/Veritasium",
        "invalid.url"  # This will fail
    ]
    
    results = await process_multiple_channels(channels)
    
    print("\nResults:")
    for channel, rss in results.items():
        status = rss if rss else "Not found"
        print(f"{channel}: {status}")

if __name__ == "__main__":
    asyncio.run(main())