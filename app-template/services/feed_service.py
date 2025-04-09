from typing import Optional, List
from urllib.parse import urlparse
from app.core.feed_parser import FeedParser
from app.crud.feed_urls import FeedURLCRUD
from app.crud.feed_news import FeedNewsCRUD
from app.schemas.feed_urls import FeedURLOut
from app.schemas.feed_news import FeedNewsItem
from app.database.mongo_db import get_feed_news_collection

class FeedService:
    @staticmethod
    async def add_feed_url(url: str) -> Optional[FeedURLOut]:
        """Add a new feed URL if it doesn't already exist"""
        normalized_url = await FeedURLCRUD.normalize_url(url)
        
        # Check if exact URL already exists
        existing_feed = await FeedURLCRUD.get_feed_url_by_url(normalized_url)
        if existing_feed:
            return existing_feed

        # Check if feed from this domain already exists
        domain = urlparse(normalized_url).netloc
        existing_domain_feed = await FeedURLCRUD.get_feed_url_by_domain(domain)
        if existing_domain_feed:
            return existing_domain_feed

        # Fetch and parse the feed
        feed_data = await FeedParser.fetch_feed(normalized_url)
        if not feed_data or hasattr(feed_data, 'bozo_exception'):
            return None

        # Parse and save feed metadata
        feed_metadata = FeedParser.parse_feed_metadata(feed_data)
        feed_metadata["url"] = normalized_url
        feed_metadata["domain"] = domain
        await FeedURLCRUD.create_feed_url(feed_metadata)

        # Parse and save feed items
        feed_items = FeedParser.parse_feed_items(feed_data, normalized_url)
        for item in feed_items:
            existing_item = await FeedNewsCRUD.get_news_item_by_link(item["link"])
            if not existing_item:
                await FeedNewsCRUD.create_feed_news_item(item)

        return await FeedURLCRUD.get_feed_url_by_url(normalized_url)

    @staticmethod
    async def get_all_feeds() -> List[FeedURLOut]:
        """Get all feeds from the database"""
        return await FeedURLCRUD.get_all_feed_urls()

    @staticmethod
    async def get_feed_items(feed_url: str, limit: int = 20) -> List[FeedNewsItem]:
        """Get items for a specific feed"""
        return await FeedNewsCRUD.get_news_items_by_feed_url(feed_url, limit)

    @staticmethod
    async def get_latest_news(limit: int = 12) -> List[FeedNewsItem]:
        """Get latest news items across all feeds"""
        collection = get_feed_news_collection()
        items = await collection.find().sort("pubDate", -1).limit(limit).to_list(limit)
        return [FeedNewsItem.from_mongo(item) for item in items if item] 

    @staticmethod
    async def get_feed_by_id(feed_id: str) -> Optional[FeedURLOut]:
        """Get a specific feed by its ID"""
        collection = FeedURLCRUD.get_feed_urls_collection()
        feed = await collection.find_one({"_id": feed_id})
        return FeedURLOut.from_mongo(feed) if feed else None

    @staticmethod
    async def get_news_items_by_feed_id(feed_id: str, limit: int = 12) -> List[FeedNewsItem]:
        """Get news items for a specific feed ID"""
        feed = await FeedService.get_feed_by_id(feed_id)
        if not feed:
            return []
        return await FeedService.get_feed_items(feed.url, limit)