import os
import aiohttp
import asyncio
import random
import functools
import logging
from functools import wraps
from urllib.parse import urlparse
from aiohttp import ClientSession, ClientTimeout

logger = logging.getLogger(__name__)

# Proxy list (make sure these are valid)
PROXY_LIST = [
    'http://ujhjjggl-rotate:m0jkp47ga63w@p.webshare.io:80',
    'http://xoztfgdf-rotate:sc8n14irsmoy@p.webshare.io:80',
    'http://gwjzgcjy-rotate:sy8mv03i745k@p.webshare.io:80',
]
MAX_RETRIES = 10  # make it configurable

def proxy(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get the session from arguments or kwargs
        session: aiohttp.ClientSession = kwargs.get('session') or (args[1] if len(args) > 1 else None)
        
        # Define your proxy URL here
        proxy_url = ''

        # If a proxy is needed, create a proxied session
        if proxy_url:
            logging.info(f"[{func.__name__}] Using proxy: {proxy_url}")
            
            # Create a TCP connector to be used with aiohttp
            connector = aiohttp.TCPConnector()

            # If no session was provided, create a new proxied session
            if not session:
                async with aiohttp.ClientSession(connector=connector, proxy=proxy_url) as proxied_session:
                    kwargs['session'] = proxied_session
                    logging.info(f"Proxy used in {func.__name__}: {proxy_url}")
                    return await func(*args, **kwargs)

            # If session is provided, continue with it
            logging.info(f"Using provided session in {func.__name__}")
            return await func(*args, **kwargs)

        # If no proxy is needed, proceed with the provided session or raise error if not present
        if session is None:
            raise ValueError("Session must be provided")
        return await func(*args, **kwargs)

    return wrapper



def retry(retries=3, delay=1, backoff=2, jitter=True, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries - 1:
                        raise
                    logger.warning(f"Retry {attempt + 1}/{retries} for {func.__name__} due to: {e}")
                    sleep_time = current_delay + random.uniform(0, 1) if jitter else current_delay
                    await asyncio.sleep(sleep_time)
                    current_delay *= backoff
        return wrapper
    return decorator

