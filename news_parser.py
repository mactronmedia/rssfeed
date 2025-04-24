import feedparser
from typing import Dict, List, Optional

class RSSFeedParser:
    """
    A class to parse and handle RSS feeds using the feedparser library.
    """
    
    @staticmethod
    def parse_feed(feed_url: str) -> Optional[Dict]:
        """
        Parse an RSS feed from the given URL.
        
        Args:
            feed_url (str): URL of the RSS feed to parse
            
        Returns:
            Optional[Dict]: Parsed feed data as a dictionary, or None if parsing fails
        """
        try:
            return feedparser.parse(feed_url)
        except Exception as e:
            print(f"Error parsing feed: {e}")
            return None
    
    @staticmethod
    def get_feed_title(feed_data: Dict) -> Optional[str]:
        """
        Extract the title from parsed feed data.
        
        Args:
            feed_data (Dict): Parsed feed data from feedparser
            
        Returns:
            Optional[str]: Feed title or None if not available
        """
        return feed_data.feed.get('title') if hasattr(feed_data, 'feed') else None
    
    @staticmethod
    def get_feed_entries(feed_data: Dict) -> List[Dict]:
        """
        Get all entries from the parsed feed data.
        
        Args:
            feed_data (Dict): Parsed feed data from feedparser
            
        Returns:
            List[Dict]: List of entry dictionaries
        """
        return feed_data.entries if hasattr(feed_data, 'entries') else []
    
    @staticmethod
    def get_entry_details(entry: Dict) -> Dict:
        """
        Extract important details from a single feed entry.
        
        Args:
            entry (Dict): A single entry from the feed
            
        Returns:
            Dict: Dictionary containing important entry details
        """
        return {
            'title': entry.get('title'),
            'link': entry.get('link'),
            'published': entry.get('published'),
            'summary': entry.get('summary'),
            'author': entry.get('author')
        }
    
    @staticmethod
    def print_feed_summary(feed_data: Dict, max_entries: int = 5) -> None:
        """
        Print a summary of the feed including title and recent entries.
        
        Args:
            feed_data (Dict): Parsed feed data from feedparser
            max_entries (int): Maximum number of entries to display
        """
        title = RSSFeedParser.get_feed_title(feed_data)
        entries = RSSFeedParser.get_feed_entries(feed_data)
        
        print(f"\nFeed Title: {title}")
        print(f"Total Entries: {len(entries)}")
        print("\nRecent Entries:")
        
        for i, entry in enumerate(entries[:max_entries]):
            details = RSSFeedParser.get_entry_details(entry)
            print(f"\n{i+1}. {details['title']}")
            print(f"   Published: {details['published']}")
            print(f"   Link: {details['link']}")
            if details['summary']:
                summary = details['summary'][:100] + '...' if len(details['summary']) > 100 else details['summary']
                print(f"   Summary: {summary}")


# Example usage
if __name__ == "__main__":
    # Example RSS feed URL (BBC News feed)
    FEED_URL = "http://feeds.bbci.co.uk/news/rss.xml"
    
    # Parse the feed
    feed_data = RSSFeedParser.parse_feed(FEED_URL)
    
    if feed_data:
        # Print a summary of the feed
        RSSFeedParser.print_feed_summary(feed_data)
        
        # Get all entries
        entries = RSSFeedParser.get_feed_entries(feed_data)
        print(f"\nFirst entry details: {RSSFeedParser.get_entry_details(entries[0])}")
    else:
        print("Failed to parse the feed.")