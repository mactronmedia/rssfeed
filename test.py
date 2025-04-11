import requests
from bs4 import BeautifulSoup
import random
import time

# URL of the RSS feed
rss_url = "https://www.had.si/blog/"

# Proxies (replace with your actual proxy credentials if needed)
proxies = {
    'http': 'http://ujhjjggl-rotate:m0jkp47ga63w@p.webshare.io:80/',
    'https': 'http://ujhjjggl-rotate:m0jkp47ga63w@p.webshare.io:80/',
}

# List of User-Agents to randomly choose from
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
]

# Randomly select a User-Agent string
headers = {
    'User-Agent': random.choice(user_agents)
}

# Function to send GET request with retries
def get_rss_with_retries(url, retries=3):
    for attempt in range(retries):
        try:
            # Send GET request with proxy and timeout to avoid hanging indefinitely
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raises an error for HTTP error responses (e.g., 404, 500)
            
            # Print the raw response text (for debugging purposes)
            print("Raw Response:")
            print(response.text)  # This will print the raw HTML or RSS feed content
            
            # Check the content type to determine if it's HTML or RSS feed
            if 'html' in response.headers['Content-Type']:
                soup = BeautifulSoup(response.content, 'html.parser')
                print("\nParsed HTML:")
                print(soup.prettify())  # Print parsed HTML if it is not an RSS feed
            else:
                print("\nThis appears to be a valid RSS feed.")  # If it's a valid RSS feed

            return response  # Exit the function after a successful request
            
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2)  # Wait a little before retrying (avoid hitting the server too quickly)

    print("Max retries reached. Could not fetch the RSS feed.")
    return None

# Run the function to fetch the RSS feed
get_rss_with_retries(rss_url)
