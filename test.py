import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
from typing import Optional, Dict, List, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define all relevant namespaces
NAMESPACES = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'atom': 'http://www.w3.org/2005/Atom',
    'atom03': 'http://purl.org/atom/ns#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'rssfake': 'http://purl.org/rss/1.0/',
    'media': 'http://search.yahoo.com/mrss/',
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'abcnews': 'http://abcnews.com/content/',
}

class MediaContent:
    """Class to represent media content with all possible attributes"""
    def __init__(self, media_type: str, url: str, **kwargs):
        self.type = media_type
        self.url = url
        self.attributes = kwargs  # Store all other attributes
        
    def __str__(self):
        attrs = ', '.join(f"{k}={v}" for k, v in self.attributes.items())
        return f"MediaContent(type={self.type}, url={self.url}, {attrs})"

class RSSItem:
    """Class to represent an RSS item with all possible fields"""
    def __init__(self):
        self.title: Optional[str] = None
        self.description: Optional[str] = None
        self.link: Optional[str] = None
        self.guid: Optional[str] = None
        self.pub_date: Optional[datetime] = None
        self.creators: List[str] = []
        self.authors: List[str] = []
        self.categories: List[str] = []
        self.content: Optional[str] = None
        self.media_content: List[MediaContent] = []
        self.media_thumbnails: List[MediaContent] = []
        self.media_keywords: List[str] = []
        self.enclosures: List[Dict] = []

    def __str__(self):
        return (f"RSSItem(title={self.title}, link={self.link}, "
                f"pub_date={self.pub_date}, media_count={len(self.media_content)})")

def parse_date(date_str: str) -> Optional[datetime]:
    """Try to parse various date formats found in RSS feeds"""
    date_formats = [
        '%a, %d %b %Y %H:%M:%S %z',  # RFC 2822
        '%a, %d %b %Y %H:%M:%S %Z',  # RFC 2822 with timezone name
        '%Y-%m-%dT%H:%M:%S%z',       # ISO 8601
        '%Y-%m-%dT%H:%M:%S',         # ISO 8601 without timezone
        '%Y-%m-%d %H:%M:%S',         # Common alternative
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def fetch_feed(url: str, timeout: int = 10) -> Optional[ET.Element]:
    """Fetch and parse the RSS feed"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; RSSParser/1.0)',
            'Accept': 'application/xml'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Handle potential encoding issues
        response.encoding = response.apparent_encoding
        
        try:
            return ET.fromstring(response.content)
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Failed to fetch RSS feed: {e}")
        return None

def parse_media_element(media_elem: ET.Element) -> MediaContent:
    """Parse a media element into a MediaContent object"""
    media_type = media_elem.get('type', '')
    url = media_elem.get('url', '')
    
    # Collect all attributes
    attributes = {}
    for attr in media_elem.attrib:
        if attr not in ('type', 'url'):
            attributes[attr] = media_elem.get(attr)
    
    return MediaContent(media_type, url, **attributes)

def parse_item(item: ET.Element) -> RSSItem:
    """Parse an individual RSS item"""
    rss_item = RSSItem()
    
    # Basic fields
    rss_item.title = get_text(item, 'title')
    rss_item.description = get_text(item, 'description')
    rss_item.link = get_text(item, 'link')
    rss_item.guid = get_text(item, 'guid')
    
    # Date parsing
    pub_date = get_text(item, 'pubDate')
    if pub_date:
        rss_item.pub_date = parse_date(pub_date)
    
    # Creator/Author information
    dc_creator = item.findall('dc:creator', NAMESPACES)
    if dc_creator:
        rss_item.creators = [creator.text for creator in dc_creator if creator.text]
    
    atom_author = item.find('atom:author/atom:name', NAMESPACES)
    if atom_author is not None and atom_author.text:
        rss_item.authors.append(atom_author.text)
    
    # Content
    rss_item.content = get_text(item, 'content:encoded', NAMESPACES)
    
    # Categories
    categories = item.findall('category')
    if categories:
        rss_item.categories = [cat.text for cat in categories if cat.text]
    
    # Media content (Media RSS)
    media_content = item.findall('media:content', NAMESPACES)
    for media in media_content:
        rss_item.media_content.append(parse_media_element(media))
    
    # Media thumbnails
    media_thumbnails = item.findall('media:thumbnail', NAMESPACES)
    for thumb in media_thumbnails:
        rss_item.media_thumbnails.append(parse_media_element(thumb))
    
    # Media keywords
    media_keywords = item.find('media:keywords', NAMESPACES)
    if media_keywords is not None and media_keywords.text:
        rss_item.media_keywords = [kw.strip() for kw in media_keywords.text.split(',')]
    
    # Enclosures
    enclosure = item.find('enclosure')
    if enclosure is not None:
        enc_info = {
            'url': enclosure.get('url'),
            'type': enclosure.get('type'),
            'length': enclosure.get('length')
        }
        rss_item.enclosures.append(enc_info)
    
    return rss_item

def get_text(element: ET.Element, path: str, namespaces: Dict = None) -> Optional[str]:
    """Helper function to safely get text from an element"""
    elem = element.find(path, namespaces)
    if elem is not None:
        return elem.text.strip() if elem.text else None
    return None

def parse_feed(root: ET.Element) -> List[RSSItem]:
    """Parse the entire RSS feed"""
    items = []
    
    # Handle different RSS/Atom formats
    if root.tag == 'rss':
        # RSS 2.0 format
        channel = root.find('channel')
        if channel is not None:
            items = channel.findall('item')
    elif root.tag.endswith('feed'):
        # Atom format
        items = root.findall('atom:entry', NAMESPACES)
    else:
        # Possibly RDF format
        items = root.findall('rssfake:item', NAMESPACES)
    
    return [parse_item(item) for item in items]

def print_item_details(item: RSSItem):
    """Print details of an RSS item in a readable format"""
    print("\n--- New Item ---")
    print(f"Title: {item.title}")
    
    if item.creators:
        print("Creators:", ", ".join(item.creators))
    if item.authors:
        print("Authors:", ", ".join(item.authors))
    
    print(f"Link: {item.link}")
    
    if item.pub_date:
        print(f"Published: {item.pub_date.strftime('%Y-%m-%d %H:%M')}")
    
    if item.categories:
        print("Categories:", ", ".join(item.categories))
    
    if item.content:
        content_preview = item.content[:150].replace('\n', ' ').strip()
        print(f"Content preview: {content_preview}...")
    
    if item.media_content:
        print(f"\nMedia content ({len(item.media_content)} items):")
        for media in item.media_content:
            print(f"  - {media}")
    
    if item.media_thumbnails:
        print(f"\nThumbnails ({len(item.media_thumbnails)} items):")
        for thumb in item.media_thumbnails[:3]:  # Show first 3 thumbnails
            print(f"  - {thumb.url} ({thumb.attributes.get('width', '?')}x{thumb.attributes.get('height', '?')})")
        if len(item.media_thumbnails) > 3:
            print(f"  + {len(item.media_thumbnails)-3} more thumbnails...")
    
    if item.media_keywords:
        print("\nKeywords:", ", ".join(item.media_keywords))
    
    if item.enclosures:
        print(f"\nEnclosures ({len(item.enclosures)} items)")

def main():
    # Example URL from your sample (though we could use any RSS feed)
    url = 'https://www.cbsnews.com/latest/rss/main'
    
    root = fetch_feed(url)
    if root is None:
        logger.error("Could not fetch or parse the feed")
        return
    
    feed_items = parse_feed(root)
    
    print(f"\nFound {len(feed_items)} items in the feed\n")
    for item in feed_items[:5]:  # Limit to first 5 items for demo
        print_item_details(item)
    
    # Example: save first item's media info
    if feed_items and feed_items[0].media_thumbnails:
        first_thumbnail = feed_items[0].media_thumbnails[0]
        logger.info(f"First thumbnail URL: {first_thumbnail.url}")

if __name__ == '__main__':
    main()