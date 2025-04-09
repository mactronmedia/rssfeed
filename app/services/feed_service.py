from typing import Optional
from urllib.parse import urlparse
from app.core.feed_parser import FeedParser
from app.crud.feed_urls import FeedURLCRUD
from app.crud.feed_news import FeedNewsCRUD
from app.schemas.feed_urls import FeedURLOut

class FeedService:
    @staticmethod
    async def add_feed_url(url: str) -> Optional[FeedURLOut]:
        # Normalize the URL to prevent duplicates or differences in format
        normalized_url = await FeedURLCRUD.normalize_url(url)
        
        # Check if the feed already exists based on the URL
        existing_feed = await FeedURLCRUD.get_feed_url_by_url(normalized_url)
        if existing_feed:
            return existing_feed

        # Check if the feed from the same domain already exists
        domain = urlparse(normalized_url).netloc
        existing_domain_feed = await FeedURLCRUD.get_feed_url_by_domain(domain)
        if existing_domain_feed:
            return existing_domain_feed

        # Try to fetch the feed data (RSS XML)
        feed_data = await FeedParser.fetch_feed(normalized_url)
        if not feed_data or hasattr(feed_data, 'bozo_exception'):
            return None

        # Parse the feed metadata and add it to the database
        feed_metadata = FeedParser.parse_feed_metadata(feed_data)
        feed_metadata["url"] = normalized_url
        feed_metadata["domain"] = domain

        # Save the feed metadata to the database
        await FeedURLCRUD.create_feed_url(feed_metadata)

        # Parse feed items (news articles) and save them to the database
        feed_items = FeedParser.parse_feed_items(feed_data, normalized_url)
        for item in feed_items:
            existing_item = await FeedNewsCRUD.get_news_item_by_link(item["link"])
            if not existing_item:
                await FeedNewsCRUD.create_feed_news_item(item)

        # Return the created feed metadata
        return await FeedURLCRUD.get_feed_url_by_url(normalized_url)

    @staticmethod
    async def get_all_feeds():
        return await FeedURLCRUD.get_all_feed_urls()

    @staticmethod
    async def get_feed_items(feed_url: str, limit: int = 20):
        return await FeedNewsCRUD.get_news_items_by_feed_url(feed_url, limit)
