import asyncio
import logging
from aiohttp import ClientSession, ClientTimeout

# Ensure logging is configured
logging.basicConfig(level=logging.INFO)

# Your health check function
async def check_youtube_proxy_health(session: ClientSession, proxy: str) -> bool:
    """Check if a proxy is able to access YouTube successfully."""
    youtube_url = "https://www.youtube.com"
    try:
        timeout = ClientTimeout(total=10)
        async with session.get(youtube_url, proxy=proxy, timeout=timeout) as response:
            if response.status == 200:
                html = await response.text()
                # Check if YouTube's consent form page is not triggered
                if 'consent.youtube.com' in html:
                    logging.warning(f"Consent form triggered on {proxy}")
                    return False  # Proxy triggered consent form, not healthy
                logging.info(f"Proxy {proxy} is healthy (can access YouTube).")
                return True
            else:
                logging.warning(f"Non-200 status code ({response.status}) for proxy: {proxy}")
                return False
    except Exception as e:
        logging.error(f"Error while checking YouTube via proxy {proxy}: {e}")
        return False

# Main async function
async def main():
    # Create an aiohttp ClientSession
    async with ClientSession() as session:
        # Proxy to test
        proxy = 'http://ujhjjggl-rotate:m0jkp47ga63w@p.webshare.io:80'

        # Loop to check 10 times
        for i in range(10):
            print(f"Attempt {i+1}/10")
            is_healthy = await check_youtube_proxy_health(session, proxy)
            if is_healthy:
                print(f"Proxy {proxy} is healthy!")
            else:
                print(f"Proxy {proxy} is not healthy.")
            # Optional: Add a small delay between attempts
            await asyncio.sleep(1)

# Run the event loop
if __name__ == "__main__":
    asyncio.run(main())
