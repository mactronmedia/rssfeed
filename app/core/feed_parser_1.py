import feedparser
from typing import Optional, Dict, Any
from enum import Enum
import logging
from urllib.parse import urlparse
import re

class FeedType(Enum):
    NEWS = 'news'
    VIDEO = 'video'
    PODCAST = 'podcast'
    BLOG = 'blog'
    UNKNOWN = 'unknown'

class FeedProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_feed_details(self, feed_url: str) -> Dict[str, Any]:
        """Fetch and analyze feed to determine its type and extract metadata."""
        try:
            feed = feedparser.parse(feed_url)
            
            if feed.get('bozo', False):
                self.logger.warning(f"Feed parsing error: {feed.bozo_exception}")
            
            feed_type = self._determine_feed_type(feed)
            domain = self._extract_domain(feed_url)
            
            return {
                'type': feed_type.value,
                'title': self._get_feed_title(feed),
                'description': feed.feed.get('description', ''),
                'domain': domain,
                'language': feed.feed.get('language', '').lower()[:2],
                'favicon': self._find_favicon(feed, domain),
                'categories': self._extract_categories(feed),
                'metadata': {
                    'etag': feed.get('etag', ''),
                    'modified': feed.get('modified', '')
                }
            }
        except Exception as e:
            self.logger.error(f"Error processing feed {feed_url}: {str(e)}")
            raise

    def _determine_feed_type(self, feed) -> FeedType:
        """Determine the most likely type of feed."""
        # Check namespaces first
        namespaces = feed.get('namespaces', {})
        if 'yt' in namespaces or any('youtube.com' in link.get('href', '') for link in feed.feed.get('links', [])):
            return FeedType.VIDEO
        
        if 'itunes' in namespaces:
            return FeedType.PODCAST
        
        # Check entries for media content
        podcast_clues = 0
        video_clues = 0
        
        for entry in feed.entries[:10]:  # Check first 10 entries
            if 'enclosures' in entry or 'enclosure' in entry:
                for enc in entry.get('enclosures', []):
                    if enc.get('type', '').startswith('audio/'):
                        podcast_clues += 2
                    elif enc.get('type', '').startswith('video/'):
                        video_clues += 2
            
            if 'yt_videoid' in entry:
                video_clues += 3
            
            if 'itunes_episode' in entry:
                podcast_clues += 3
        
        # Determine type based on clues
        if video_clues > podcast_clues and video_clues >= 2:
            return FeedType.VIDEO
        elif podcast_clues > video_clues and podcast_clues >= 2:
            return FeedType.PODCAST
        elif 'blog' in feed.feed.get('generator', '').lower():
            return FeedType.BLOG
        else:
            return FeedType.NEWS

    def _get_feed_title(self, feed) -> Dict[str, str]:
        """Extract and normalize feed title."""
        title = feed.feed.get('title', 'Untitled Feed')
        return {
            'text': title,
            'normalized': self._normalize_text(title)
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for search and comparison."""
        return re.sub(r'[^\w\s]', '', text.lower().strip())
    
    def _extract_domain(self, url: str) -> str:
        """Extract root domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    def _find_favicon(self, feed, domain: str) -> str:
        """Try to find favicon URL."""
        # Check feed links first
        for link in feed.feed.get('links', []):
            if 'icon' in link.get('rel', ''):
                return link.get('href', '')
        
        # Fallback to common favicon locations
        return f"https://{domain}/favicon.ico"
    
    def _extract_categories(self, feed) -> list:
        """Extract categories from feed."""
        categories = set()
        
        # Feed-level categories
        for cat in feed.feed.get('categories', []):
            if isinstance(cat, dict):
                categories.add(cat.get('term', '').lower())
            else:
                categories.add(cat.lower())
        
        # Entry-level categories (sample first 5 entries)
        for entry in feed.entries[:5]:
            for cat in entry.get('categories', []):
                if isinstance(cat, dict):
                    categories.add(cat.get('term', '').lower())
                else:
                    categories.add(cat.lower())
        
        return [c for c in categories if c and len(c) < 50]

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    processor = FeedProcessor()
    
    test_feeds = [
        'https://feeds.bbci.co.uk/news/rss.xml',
        'https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw',
        'https://feeds.megaphone.fm/GLTZ8934989483'
    ]
    
    for feed_url in test_feeds:
        try:
            details = processor.get_feed_details(feed_url)
            print(f"\nFeed: {feed_url}")
            print(f"Type: {details['type']}")
            print(f"Title: {details['title']['text']}")
            print(f"Domain: {details['domain']}")
            print(f"Categories: {details['categories']}")
        except Exception as e:
            print(f"Failed to process {feed_url}: {str(e)}")