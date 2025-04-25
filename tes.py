import requests
from bs4 import BeautifulSoup
import random
import time

url = "https://www.washingtonpost.com/nation/2025/04/24/bmw-trump-trade-tariffs-south-carolina-spartanburg/"

user_agents = [
    # Add more if needed
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Safari/605.1.15',
]

proxies = {
    "http": "http://gwjzgcjy-rotate:sy8mv03i745k@p.webshare.io:80",
    "https": "http://gwjzgcjy-rotate:sy8mv03i745k@p.webshare.io:80"
}

headers = {
    'User-Agent': random.choice(user_agents)
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    print(soup.prettify())

        # Method 2: Alternative approach to get og:image as fallback
    og_image = soup.find('meta', property='og:image')
    if og_image:
        print("og:image:", og_image['content'])

except requests.exceptions.SSLError:
    print("SSL handshake failed — site may be blocking the proxy.")
except requests.exceptions.ProxyError:
    print("Proxy worked, but was likely blocked by the target site.")
except requests.exceptions.RequestException as e:
    print(f"General request error: {e}")
