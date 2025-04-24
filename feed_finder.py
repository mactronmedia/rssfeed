import requests
import feedparser
import urllib.parse
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from typing import List, Optional
import random
import os


class FeedFinder:
    # List of common user agents
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.5; rv:109.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
    ]

    def __init__(self, timeout: int = 10, user_agent: str = None):
        """
        Initialize the FeedFinder with configurable parameters.
        
        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string (optional)
        """
        self.timeout = timeout
        self.user_agent = user_agent or self._get_random_user_agent()
        self.session = requests.Session()
        self.session.headers.update(self._get_headers())

    @classmethod
    def _get_random_user_agent(cls) -> str:
        """Get a random user agent from the list or environment variable."""
        # Check environment variable first
        env_agents = [ua for ua in os.getenv('USER_AGENTS', "").split(",") if ua.strip()]
        if env_agents:
            return random.choice(env_agents)
        return random.choice(cls.USER_AGENTS)

    def _get_headers(self) -> dict:
        """Return headers with random user agent and common request headers."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.google.com/",
            "DNT": "1"
        }

    def _can_fetch(self, url: str) -> bool:
        """Check if we're allowed to fetch this URL based on robots.txt."""
        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        rp = RobotFileParser()
        try:
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            return True
    
    def _get_page(self, url: str) -> Optional[str]:
        """Safely fetch a web page with error handling."""
        if not self._can_fetch(url):
            print(f"Blocked by robots.txt: {url}")
            return None
            
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                return None
                
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {str(e)[:100]}...")
            return None
    
    def _find_possible_feeds(self, html: str, base_url: str) -> List[str]:
        """Find possible feed URLs in HTML content."""
        soup = BeautifulSoup(html, 'html.parser')
        possible_feeds = set()
        
        # Check RSS/Atom link tags
        for link in soup.find_all("link", rel="alternate"):
            href = link.get("href")
            feed_type = link.get("type", "").lower()
            if href and any(x in feed_type for x in ["rss", "xml", "atom"]):
                possible_feeds.add(self._normalize_url(href, base_url))
        
        # Check for common feed patterns in links
        common_patterns = ["feed", "rss", "xml", "atom", "rdf"]
        for a in soup.find_all("a", href=True):
            href = a['href'].lower()
            if any(pattern in href for pattern in common_patterns):
                possible_feeds.add(self._normalize_url(a['href'], base_url))
        
        # Check common feed paths
        common_paths = [
            "/feed", "/rss", "/atom", "/feed.xml",
            "/rss.xml", "/atom.xml", "/index.xml",
            "/.rss", "/.atom", "/.xml"
        ]
        for path in common_paths:
            possible_feeds.add(urllib.parse.urljoin(base_url, path))
            
        return list(possible_feeds)
    
    def _normalize_url(self, url: str, base_url: str) -> str:
        """Normalize a URL by making it absolute."""
        if url.startswith(('http://', 'https://')):
            return url
        return urllib.parse.urljoin(base_url, url)
    
    def _validate_feed(self, url: str) -> bool:
        """Validate if a URL is a working feed."""
        try:
            # First check headers to avoid downloading large files
            head = self.session.head(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                headers=self._get_headers()
            )
            content_type = head.headers.get('content-type', '').lower()
            
            if not any(x in content_type for x in ['xml', 'rss', 'atom', 'text/xml', 'application/xml']):
                return False
                
            # Now parse the feed
            feed = feedparser.parse(url)
            return bool(feed.entries) or ('title' in feed.feed)
        except Exception as e:
            print(f"Error validating feed {url}: {str(e)[:100]}...")
            return False
    
    @staticmethod
    def findfeed(site: str) -> List[str]:
        """
        Static method to maintain compatibility with original interface.
        """
        finder = FeedFinder()
        
        if not site.startswith(('http://', 'https://')):
            site = f"https://{site}"
            
        parsed_url = urllib.parse.urlparse(site)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        html = finder._get_page(site)
        if not html:
            return []
        
        possible_feeds = finder._find_possible_feeds(html, base_url)
        valid_feeds = [url for url in possible_feeds if finder._validate_feed(url)]
        
        return valid_feeds


if __name__ == "__main__":
    # Example usage
    sites = [
        'https://www.politico.com/',
    ]
    
    for site in sites:
        print(f"\nChecking {site}...")
        feed_urls = FeedFinder.findfeed(site)
        
        if feed_urls:
            print(f"Found {len(feed_urls)} feed(s):")
            for url in feed_urls:
                print(f"- {url}")
        else:
            print("No feeds found")