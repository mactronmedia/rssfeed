import feedparser

def extract_images_from_cbs_feed(feed_url):
    # Parse the RSS feed
    feed = feedparser.parse(feed_url)
    
    images = []
    
    print(f"Feed status: {feed.status}")
    print(f"Number of entries: {len(feed.entries)}")
    
    # Iterate through each item in the feed
    for entry in feed.entries:
        # Debug: Print all available keys in the entry
        # print("\nAvailable keys in entry:", entry.keys())
        
        # CBS News stores image URLs in different possible locations
        image_url = None
        
        # Method 1: Check for plain 'image' attribute (works for CBS News)
        if 'image' in entry:
            image_url = entry.image
        # Method 2: Check for media:thumbnail
        elif 'media_thumbnail' in entry and entry.media_thumbnail:
            image_url = entry.media_thumbnail[0]['url']
        # Method 3: Check for media:content
        elif 'media_content' in entry and entry.media_content:
            for media in entry.media_content:
                if media.get('type', '').startswith('image/'):
                    image_url = media['url']
                    break
        
        if image_url:
            images.append({
                'title': entry.get('title', 'No title'),
                'image_url': image_url,
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'description': entry.get('description', '')
            })
    
    return images

# Example usage with the CBS News RSS feed
cbs_rss_url = "https://www.cbsnews.com/latest/rss/main"
images = extract_images_from_cbs_feed(cbs_rss_url)

if not images:
    print("\nNo images found in the feed. Trying alternative parsing method...")
    
    # Alternative method - parse the raw XML if feedparser doesn't work
    import requests
    from xml.etree import ElementTree as ET
    
    try:
        response = requests.get(cbs_rss_url)
        root = ET.fromstring(response.content)
        namespace = {'media': 'http://search.yahoo.com/mrss/'}
        
        images = []
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else 'No title'
            link = item.find('link').text if item.find('link') is not None else ''
            
            # Check for image in media:thumbnail
            thumbnail = item.find('media:thumbnail', namespace)
            if thumbnail is not None:
                image_url = thumbnail.attrib['url']
            else:
                # Check for plain image tag
                image_tag = item.find('image')
                image_url = image_tag.text if image_tag is not None else None
            
            if image_url:
                images.append({
                    'title': title,
                    'image_url': image_url,
                    'link': link,
                    'published': item.find('pubDate').text if item.find('pubDate') is not None else '',
                    'description': item.find('description').text if item.find('description') is not None else ''
                })
        
        print(f"Found {len(images)} images using alternative method")
    except Exception as e:
        print(f"Failed to parse feed with alternative method: {e}")

# Print results if we found any images
if images:
    print(f"\nFound {len(images)} images in the feed:\n")
    for idx, img in enumerate(images[:5], 1):  # Only show first 5 for brevity
        print(f"{idx}. {img['title']}")
        print(f"   Published: {img['published']}")
        print(f"   Image URL: {img['image_url']}")
        print(f"   Article URL: {img['link']}")
        print(f"   Description: {img['description'][:100]}...\n")
    
    if len(images) > 5:
        print(f"... plus {len(images)-5} more images")
else:
    print("\nNo images found after trying all methods. The feed structure may have changed.")