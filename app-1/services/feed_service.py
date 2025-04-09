from typing import Optional
from app.core.feed_parser import FeedParser
from app.crud.feed_urls import FeedURLCRUD
from app.crud.feed_news import FeedNewsCRUD
from app.schemas.feed_urls import FeedURLOut

class FeedService:
    @staticmethod
    async def add_feed_url(url: str) -> Optional[FeedURLOut]:
        # Check if feed already exists
        existing_feed = await FeedURLCRUD.get_feed_url_by_url(url)
        if existing_feed:
            return existing_feed

        # Fetch and parse feed
        feed_data = await FeedParser.fetch_feed(url)
        if not feed_data or hasattr(feed_data, 'bozo_exception'):
            return None

        # Parse metadata
        feed_metadata = FeedParser.parse_feed_metadata(feed_data)
        feed_metadata["url"] = url

        # Save feed metadata
        await FeedURLCRUD.create_feed_url(feed_metadata)

        # Parse and save feed items
        feed_items = FeedParser.parse_feed_items(feed_data, url)
        for item in feed_items:
            existing_item = await FeedNewsCRUD.get_news_item_by_link(item["link"])
            if not existing_item:
                await FeedNewsCRUD.create_feed_news_item(item)

        return await FeedURLCRUD.get_feed_url_by_url(url)

    @staticmethod
    async def get_all_feeds():
        return await FeedURLCRUD.get_all_feed_urls()

    @staticmethod
    async def get_feed_items(feed_url: str, limit: int = 20):
        return await FeedNewsCRUD.get_news_items_by_feed_url(feed_url, limit)