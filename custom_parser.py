import asyncio
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse
import aiohttp
from lxml import etree
from lxml.etree import XMLSyntaxError

class RSSParserUtils:
    """Utility methods for RSS parsing"""
    
    @staticmethod
    def get_random_headers() -> Dict[str, str]:
        """Return random headers to mimic different browsers"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        ]
        return {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",
        }
    
    @staticmethod
    def parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse various date formats from RSS feeds"""
        if not date_str:
            return None
        try:
            # Try ISO 8601 format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass
        # Add more date formats as needed
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
            "%a, %d %b %Y %H:%M:%S %Z",  # RFC 2822 with timezone name
            "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601
            "%Y-%m-%d %H:%M:%S",          # Simple format
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

class BaseFeedParser:
    """Base class for all feed parsers"""
    
    NAMESPACES = {
        'atom': 'http://www.w3.org/2005/Atom',
        'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
        'media': 'http://search.yahoo.com/mrss/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'yt': 'http://www.youtube.com/xml/schemas/2015'
    }
    
    @classmethod
    def _get_text(cls, element: etree._Element, path: str, namespace: Optional[str] = None) -> Optional[str]:
        """Helper to get text from an element with optional namespace"""
        if namespace:
            ns = cls.NAMESPACES.get(namespace)
            if ns is None:
                return None
            elem = element.find(path, namespaces={namespace: ns})
        else:
            elem = element.find(path)
        return elem.text if elem is not None else None

    @staticmethod
    async def fetch_feed(url: str, session: aiohttp.ClientSession, timeout: int = 10) -> Optional[str]:
        """Fetch feed content with timeout"""
        try:
            headers = RSSParserUtils.get_random_headers()
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    return await response.text()
                return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
    
    @staticmethod
    def parse_xml(content: str) -> Optional[etree._Element]:
        """Parse XML content with error handling"""
        try:
            parser = etree.XMLParser(recover=True, remove_blank_text=True)
            root = etree.fromstring(content.encode(), parser=parser)
            return root if root is not None else None  # Explicit None check
        except (XMLSyntaxError, ValueError) as e:
            print(f"XML parsing error: {str(e)}")
            return None
    
    @classmethod
    def parse_feed_metadata(cls, root: etree._Element) -> Dict[str, Optional[str]]:
        """Parse common feed metadata"""
        raise NotImplementedError
    
    @classmethod
    def parse_feed_items(cls, root: etree._Element) -> List[Dict[str, Optional[str]]]:
        """Parse feed items"""
        raise NotImplementedError

class TextFeedParser(BaseFeedParser):
    """Parser for standard RSS and Atom text feeds"""
    
    @classmethod
    def parse_feed_metadata(cls, root: etree._Element) -> Dict[str, Optional[str]]:
        """Parse feed metadata for standard RSS/Atom feeds"""
        metadata = {
            'title': None,
            'link': None,
            'description': None,
            'image': None,
            'language': None,
            'pub_date': None,
            'last_build_date': None,
        }
        
        # RSS format
        channel = root.find('channel')
        if channel is not None:
            metadata['title'] = cls._get_text(channel, 'title')
            metadata['link'] = cls._get_text(channel, 'link')
            metadata['description'] = cls._get_text(channel, 'description')
            metadata['language'] = cls._get_text(channel, 'language')
            metadata['pub_date'] = RSSParserUtils.parse_date(cls._get_text(channel, 'pubDate'))
            metadata['last_build_date'] = RSSParserUtils.parse_date(cls._get_text(channel, 'lastBuildDate'))
            
            # Handle image
            image = channel.find('image')
            if image is not None:
                metadata['image'] = cls._get_text(image, 'url')
        
        # Atom format
        else:
            metadata['title'] = cls._get_text(root, 'title', namespace='atom')
            metadata['link'] = cls._get_link(root)
            metadata['description'] = cls._get_text(root, 'subtitle', namespace='atom')
            metadata['pub_date'] = RSSParserUtils.parse_date(cls._get_text(root, 'updated', namespace='atom'))
        
        return metadata
    
    @classmethod
    def parse_feed_items(cls, root: etree._Element) -> List[Dict[str, Optional[str]]]:
        """Parse items for standard RSS/Atom feeds"""
        items = []
        
        # RSS format
        channel = root.find('channel')
        if channel is not None:
            for item in channel.findall('item'):
                items.append(cls._parse_rss_item(item))
        
        # Atom format
        else:
            for entry in root.findall('atom:entry', namespaces=cls.NAMESPACES):
                items.append(cls._parse_atom_item(entry))
        
        return items
    
    @classmethod
    def _parse_rss_item(cls, item: etree._Element) -> Dict[str, Optional[str]]:
        """Parse individual RSS item"""
        return {
            'title': cls._get_text(item, 'title'),
            'link': cls._get_text(item, 'link'),
            'description': cls._get_text(item, 'description') or cls._get_text(item, 'content:encoded', namespace='content'),
            'image': cls._get_media_content(item),
            'pub_date': RSSParserUtils.parse_date(cls._get_text(item, 'pubDate')),
            'guid': cls._get_text(item, 'guid'),
            'author': cls._get_text(item, 'author') or cls._get_text(item, 'dc:creator', namespace='dc'),
        }
    
    @classmethod
    def _parse_atom_item(cls, entry: etree._Element) -> Dict[str, Optional[str]]:
        """Parse individual Atom entry"""
        return {
            'title': cls._get_text(entry, 'atom:title', namespace='atom'),
            'link': cls._get_link(entry, namespace='atom'),
            'description': cls._get_text(entry, 'atom:summary', namespace='atom'),
            'image': cls._get_media_content(entry),
            'pub_date': RSSParserUtils.parse_date(cls._get_text(entry, 'atom:updated', namespace='atom')),
            'guid': cls._get_text(entry, 'atom:id', namespace='atom'),
            'author': cls._get_text(entry, 'atom:author/atom:name', namespace='atom'),
        }
        
    @classmethod
    def _get_link(cls, element: etree._Element, namespace: Optional[str] = None) -> Optional[str]:
        """Get link from Atom feed"""
        if namespace:
            ns = cls.NAMESPACES.get(namespace)
            links = element.findall(f"{namespace}:link", namespaces={namespace: ns}) if ns else []
        else:
            links = element.findall('link')
        
        for link in links:
            if link.get('rel') == 'alternate' or link.get('rel') is None:
                return link.get('href')
        return None
    
    @classmethod
    def _get_media_content(cls, element: etree._Element) -> Optional[str]:
        """Get media content (image) from item"""
        # Check Media RSS namespace first
        media_content = element.find('media:content', namespaces=cls.NAMESPACES)
        if media_content is not None and media_content.get('url'):
            return media_content.get('url')
        
        # Check enclosure in RSS
        enclosure = element.find('enclosure')
        if enclosure is not None and enclosure.get('type', '').startswith('image/'):
            return enclosure.get('url')
        
        # Check for itunes image
        itunes_image = element.find('itunes:image', namespaces=cls.NAMESPACES)
        if itunes_image is not None and itunes_image.get('href'):
            return itunes_image.get('href')
        
        return None

class PodcastFeedParser(BaseFeedParser):
    """Parser for podcast feeds (iTunes compatible)"""
    
    @classmethod
    def parse_feed_metadata(cls, root: etree._Element) -> Dict[str, Optional[str]]:
        """Parse podcast feed metadata"""
        channel = root.find('channel')
        if channel is None:
            return {}
            
        metadata = {
            'title': cls._get_text(channel, 'title'),
            'link': cls._get_text(channel, 'link'),
            'description': cls._get_text(channel, 'description') or cls._get_text(channel, 'itunes:summary', namespace='itunes'),
            'image': cls._get_text(channel, 'itunes:image', namespace='itunes') or cls._get_image_url(channel),
            'language': cls._get_text(channel, 'language'),
            'pub_date': RSSParserUtils.parse_date(cls._get_text(channel, 'pubDate')),
            'last_build_date': RSSParserUtils.parse_date(cls._get_text(channel, 'lastBuildDate')),
            'author': cls._get_text(channel, 'itunes:author', namespace='itunes'),
            'category': cls._get_categories(channel),
            'explicit': cls._get_text(channel, 'itunes:explicit', namespace='itunes'),
            'type': cls._get_text(channel, 'itunes:type', namespace='itunes'),
        }
        return metadata
    
    @classmethod
    def parse_feed_items(cls, root: etree._Element) -> List[Dict[str, Optional[str]]]:
        """Parse podcast items"""
        items = []
        channel = root.find('channel')
        if channel is None:
            return items
            
        for item in channel.findall('item'):
            items.append(cls._parse_podcast_item(item))
        return items
    
    @classmethod
    def _parse_podcast_item(cls, item: etree._Element) -> Dict[str, Optional[str]]:
        """Parse individual podcast item"""
        enclosure = item.find('enclosure')
        return {
            'title': cls._get_text(item, 'title'),
            'link': cls._get_text(item, 'link'),
            'description': cls._get_text(item, 'description') or cls._get_text(item, 'itunes:summary', namespace='itunes'),
            'image': cls._get_text(item, 'itunes:image', namespace='itunes') or cls._get_image_url(item),
            'pub_date': RSSParserUtils.parse_date(cls._get_text(item, 'pubDate')),
            'guid': cls._get_text(item, 'guid'),
            'author': cls._get_text(item, 'itunes:author', namespace='itunes') or cls._get_text(item, 'author'),
            'duration': cls._get_text(item, 'itunes:duration', namespace='itunes'),
            'explicit': cls._get_text(item, 'itunes:explicit', namespace='itunes'),
            'episode_type': cls._get_text(item, 'itunes:episodeType', namespace='itunes'),
            'season': cls._get_text(item, 'itunes:season', namespace='itunes'),
            'episode': cls._get_text(item, 'itunes:episode', namespace='itunes'),
            'audio_url': enclosure.get('url') if enclosure is not None else None,
            'audio_type': enclosure.get('type') if enclosure is not None else None,
            'audio_length': enclosure.get('length') if enclosure is not None else None,
        }
    
    @classmethod
    def _get_image_url(cls, element: etree._Element) -> Optional[str]:
        """Get image URL from itunes:image or standard image tag"""
        itunes_image = element.find('itunes:image', namespaces=cls.NAMESPACES)
        if itunes_image is not None and itunes_image.get('href'):
            return itunes_image.get('href')
        
        image = element.find('image')
        if image is not None:
            return cls._get_text(image, 'url')
        return None
    
    @classmethod
    def _get_categories(cls, channel: etree._Element) -> List[str]:
        """Get podcast categories"""
        categories = []
        for cat in channel.findall('itunes:category', namespaces=cls.NAMESPACES):
            if cat.get('text'):
                categories.append(cat.get('text'))
            # Handle subcategories
            subcat = cat.find('itunes:category', namespaces=cls.NAMESPACES)
            if subcat is not None and subcat.get('text'):
                categories.append(subcat.get('text'))
        return categories

class YouTubeFeedParser(BaseFeedParser):
    """Parser for YouTube RSS feeds"""
    
    @classmethod
    def parse_feed_metadata(cls, root: etree._Element) -> Dict[str, Optional[str]]:
        """Parse YouTube feed metadata"""
        metadata = {
            'title': cls._get_text(root, 'atom:title', namespace='atom'),
            'link': cls._get_youtube_link(root),
            'description': cls._get_text(root, 'atom:subtitle', namespace='atom'),
            'image': cls._get_youtube_image(root),
            'pub_date': RSSParserUtils.parse_date(cls._get_text(root, 'atom:updated', namespace='atom')),
            'youtube_channel_id': cls._get_youtube_id(root),
        }
        return metadata
    
    @classmethod
    def parse_feed_items(cls, root: etree._Element) -> List[Dict[str, Optional[str]]]:
        """Parse YouTube items"""
        items = []
        
        for entry in root.findall('atom:entry', namespaces=cls.NAMESPACES):
            items.append(cls._parse_youtube_item(entry))
        
        return items
    
    @classmethod
    def _parse_youtube_item(cls, entry: etree._Element) -> Dict[str, Optional[str]]:
        """Parse individual YouTube item"""
        media_group = entry.find('media:group', namespaces=cls.NAMESPACES)
        thumbnail = media_group.find('media:thumbnail', namespaces=cls.NAMESPACES) if media_group is not None else None
        
        return {
            'title': cls._get_text(entry, 'atom:title', namespace='atom'),
            'link': cls._get_youtube_entry_link(entry),
            'description': cls._get_text(media_group, 'media:description', namespace='media') if media_group is not None else None,
            'image': thumbnail.get('url') if thumbnail is not None else None,
            'pub_date': RSSParserUtils.parse_date(cls._get_text(entry, 'atom:published', namespace='atom')),
            'guid': cls._get_text(entry, 'atom:id', namespace='atom'),
            'author': cls._get_text(entry, 'atom:author/atom:name', namespace='atom'),
            'video_id': cls._extract_video_id(entry),
        }
    
    @classmethod
    def _get_youtube_link(cls, root: etree._Element) -> Optional[str]:
        """Get YouTube channel link"""
        for link in root.findall('atom:link', namespaces=cls.NAMESPACES):
            if link.get('rel') == 'alternate':
                return link.get('href')
        return None
    
    @classmethod
    def _get_youtube_entry_link(cls, entry: etree._Element) -> Optional[str]:
        """Get YouTube video link from entry"""
        for link in entry.findall('atom:link', namespaces=cls.NAMESPACES):
            if link.get('rel') == 'alternate':
                return link.get('href')
        return None
    
    @classmethod
    def _get_youtube_image(cls, root: etree._Element) -> Optional[str]:
        """Get YouTube channel image"""
        # Try to get from logo first
        logo = cls._get_text(root, 'atom:logo', namespace='atom')
        if logo:
            return logo
        
        # Fallback to icon
        return cls._get_text(root, 'atom:icon', namespace='atom')
    
    @classmethod
    def _get_youtube_id(cls, root: etree._Element) -> Optional[str]:
        """Extract YouTube channel ID"""
        # Try to get from yt:channelId first
        channel_id = root.findtext('yt:channelId', namespaces={'yt': cls.NAMESPACES['yt']})
        if channel_id:
            return channel_id
        
        # Fallback: extract from self link
        for link in root.findall('atom:link', namespaces=cls.NAMESPACES):
            if link.get('rel') == 'self':
                href = link.get('href')
                if href and 'channel_id=' in href:
                    return href.split('channel_id=')[1]
        return None
    
    @classmethod
    def _extract_video_id(cls, entry: etree._Element) -> Optional[str]:
        """Extract video ID from entry"""
        # First try to get from yt:videoId
        video_id = entry.findtext('yt:videoId', namespaces={'yt': cls.NAMESPACES['yt']})
        if video_id:
            return video_id
        
        # Fallback: try to extract from ID
        entry_id = cls._get_text(entry, 'atom:id', namespace='atom')
        if entry_id and 'video:' in entry_id:
            return entry_id.split('video:')[-1]
        
        # Final fallback: try to extract from link
        link = cls._get_youtube_entry_link(entry)
        if link and 'v=' in link:
            return link.split('v=')[1].split('&')[0]
        return None

class RSSParser:
    """Main RSS parser class that handles all feed types"""
    
    PARSERS = {
        'text': TextFeedParser,
        'podcast': PodcastFeedParser,
        'youtube': YouTubeFeedParser,
    }
    
    def __init__(self, max_concurrent: int = 10, timeout: int = 30):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = timeout
    
    async def parse_feed(self, url: str) -> Tuple[Dict, List[Dict]]:
        """Parse a single feed with automatic type detection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with self.semaphore:
                    content = await BaseFeedParser.fetch_feed(url, session, self.timeout)
                    if not content:
                        print(f"Failed to fetch content from {url}")
                        return {}, []
                    
                    root = BaseFeedParser.parse_xml(content)
                    if root is None:
                        print(f"Failed to parse XML from {url}")
                        return {}, []
                    
                    # Detect feed type
                    parser = self._detect_feed_type(root, url)
                    
                    # Parse feed
                    metadata = parser.parse_feed_metadata(root)
                    items = parser.parse_feed_items(root)
                    
                    return metadata, items
        except Exception as e:
            print(f"Error parsing feed {url}: {str(e)}")
            return {}, []
    
    def _detect_feed_type(self, root: etree._Element, url: str) -> BaseFeedParser:
        """Detect feed type and return appropriate parser"""
        # Check for YouTube first
        if ('youtube.com' in url or 
            root.find('.//media:group', namespaces=BaseFeedParser.NAMESPACES) is not None or
            root.find('.//yt:videoId', namespaces={'yt': 'http://www.youtube.com/xml/schemas/2015'}) is not None):
            return self.PARSERS['youtube']
        
        # Then check for Podcast
        if (root.find('.//itunes:author', namespaces=BaseFeedParser.NAMESPACES) is not None or 
            root.find('.//itunes:category', namespaces=BaseFeedParser.NAMESPACES) is not None):
            return self.PARSERS['podcast']
        
        # Default to text feed
        return self.PARSERS['text']

    async def parse_feeds(self, urls: List[str]) -> List[Tuple[Dict, List[Dict]]]:
        """Parse multiple feeds concurrently"""
        tasks = [self.parse_feed(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Ensure we always return (metadata, items) tuples
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Feed parsing error: {str(result)}")
                processed_results.append(({}, []))
            else:
                processed_results.append(result)
        
        return processed_results

async def main():
    """Enhanced example usage of the RSSParser with better output formatting and error handling."""
    # Example feeds of different types with descriptive comments
    feeds = [
        # News RSS feed
        'http://feeds.bbci.co.uk/news/rss.xml',
        # Tech news Atom feed
        'https://feeds.feedburner.com/TechCrunch/',
        # Podcast feed
        'https://aidea.libsyn.com/rss',
        # YouTube channel feed
        'https://www.youtube.com/feeds/videos.xml?channel_id=UCY1kMZp36IQSyNx_9h4mpCg',
        # Invalid feed for testing error handling
        'https://invalid.feed.url/',
    ]
    
    print("Starting RSS feed parser demonstration...")
    print(f"Processing {len(feeds)} feeds with different formats\n")
    
    parser = RSSParser(max_concurrent=5, timeout=15)
    results = await parser.parse_feeds(feeds)
    
    for idx, ((metadata, items), url) in enumerate(zip(results, feeds), 1):
        print(f"\n{'=' * 50}")
        print(f"FEED #{idx}: {url}")
        print(f"{'=' * 50}")
        
        if not metadata and not items:
            print("⚠️  Failed to parse this feed (may be invalid or unreachable)")
            continue
        
        # Print metadata with proper formatting
        print("\n📰 METADATA:")
        print(f"  Title: {metadata.get('title', 'N/A')}")
        print(f"  Link: {metadata.get('link', 'N/A')}")
        print(f"  Description: {metadata.get('description', 'No description available')}")
        print(f"  Language: {metadata.get('language', 'N/A')}")
        
        # Format dates properly
        last_updated = metadata.get('last_build_date') or metadata.get('pub_date')
        print(f"  Last Updated: {last_updated if last_updated else 'N/A'}")
        
        # Special fields for specific feed types
        if metadata.get('author'):
            print(f"  Author: {metadata['author']}")
        if metadata.get('image'):
            print(f"  Image URL: {metadata['image']}")
        
        # Print items information
        print(f"\n📝 ITEMS FOUND: {len(items)}")
        
        if items:
            # Show first 3 items (or all if less than 3)
            for i, item in enumerate(items[:3], 1):
                print(f"\n  ITEM #{i}:")
                print(f"    Title: {item.get('title', 'No title')}")
                
                # Handle description safely
                desc = item.get('description')
                if desc:
                    print(f"    Description: {desc[:150] + '...' if len(desc) > 150 else desc}")
                else:
                    print("    Description: No description available")
                
                print(f"    Published: {item.get('pub_date', 'N/A')}")
                print(f"    Link: {item.get('link', 'N/A')}")
                
                # Show media-specific fields if they exist
                if item.get('duration'):
                    print(f"    Duration: {item['duration']}")
                if item.get('audio_url'):
                    print(f"    Audio URL: {item['audio_url']}")
                if item.get('video_id'):
                    print(f"    Video ID: {item['video_id']}")
                
                # Show media thumbnail if available
                if item.get('image'):
                    print(f"    Thumbnail: {item['image']}")
            
            if len(items) > 3:
                print(f"\n  ... and {len(items) - 3} more items")
    
    print("\nFeed parsing completed!")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")