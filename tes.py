import requests
from bs4 import BeautifulSoup

url = "https://www.washingtonpost.com/world/2025/04/22/pope-francis-funeral-who-will-attend/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Method 1: Extract from figure element (specific to your example)
    figure = soup.find('figure', class_='wpds-c-dsRDLm')
    if figure:
        img = figure.find('img')
        if img and 'srcset' in img.attrs:
            # Get the first (largest) image from srcset
            image_url = img['srcset'].split(',')[0].split(' ')[0]
            print("Article main image:", image_url)
    
    # Method 2: Alternative approach to get og:image as fallback
    og_image = soup.find('meta', property='og:image')
    if og_image:
        print("og:image:", og_image['content'])

except requests.exceptions.RequestException as e:
    print(f"Error fetching the URL: {e}")
except Exception as e:
    print(f"An error occurred: {e}")