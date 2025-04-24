import feedparser
from bs4 import BeautifulSoup
import requests

# Define the RSS feed URL
rss_url = "https://www.cbsnews.com/latest/rss/main"

# Function to extract thumbnail URL from an entry
def extract_thumbnail(entry):
    # Check media_content first for images
    if 'media_content' in entry:
        for media in entry['media_content']:
            if 'url' in media:
                return media['url']

    # Check the 'content' field for image URLs
    if 'content' in entry:
        content = entry['content'][0].get('value', '')
        soup = BeautifulSoup(content, 'html.parser')
        image = soup.find('img')
        if image:
            return image.get('src')

    # Check 'enclosures' for image files (like jpg, png)
    if 'enclosures' in entry:
        for enclosure in entry['enclosures']:
            if 'url' in enclosure and (enclosure['url'].endswith('.jpg') or enclosure['url'].endswith('.png')):
                return enclosure['url']

    # If none of the above work, check summary or description fields for embedded images
    if 'summary' in entry:
        soup = BeautifulSoup(entry['summary'], 'html.parser')
        image = soup.find('img')
        if image:
            return image.get('src')

    return None  # Return None if no image found


# Function to parse the RSS feed with custom headers
def parse_feed(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    
    # Send a request with custom headers to avoid bot protection
    response = requests.get(url, headers=headers)
    feed = feedparser.parse(response.text)
    
    thumbnails = []
    for entry in feed.entries:
        thumbnail_url = extract_thumbnail(entry)
        if thumbnail_url:
            thumbnails.append(thumbnail_url)
    
    return thumbnails

# Main function
if __name__ == "__main__":
    thumbnails = parse_feed(rss_url)

    # Print all extracted thumbnail URLs
    if thumbnails:
        print("Extracted Thumbnails:")
        for thumbnail in thumbnails:
            print(thumbnail)
    else:
        print("No thumbnails found.")
