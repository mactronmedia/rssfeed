# services/feed_service.py

import aiohttp
from typing import Optional
from urllib.parse import urlparse
from app.core.feed_parser import FeedParser
from app.crud.feed_urls import FeedURLCRUD
from app.crud.feed_news import FeedNewsCRUD
from app.schemas.feed_urls import FeedURLOut

class FeedService:
    @staticmethod
    async def add_feed_url(url: str) -> Optional[FeedURLOut]:
        normalized_url = await FeedURLCRUD.normalize_url(url)
        
        existing_feed = await FeedURLCRUD.get_feed_url_by_url(normalized_url)
        if existing_feed:
            return existing_feed

        domain = urlparse(normalized_url).netloc
        existing_domain_feed = await FeedURLCRUD.get_feed_url_by_domain(domain)
        if existing_domain_feed:
            return existing_domain_feed

        async with aiohttp.ClientSession() as session:
            feed_data = await FeedParser.fetch_feed(normalized_url, session)
            if not feed_data or hasattr(feed_data, 'bozo_exception'):
                return None

            feed_metadata = FeedParser.parse_feed_metadata(feed_data)
            feed_metadata["url"] = normalized_url
            feed_metadata["domain"] = domain

            # Insert feed metadata into the database
            await FeedURLCRUD.create_feed_url(feed_metadata)

            # Parse the feed items (news articles)
            feed_items = await FeedParser.parse_feed_items(feed_data, normalized_url, session)

        # Get existing links from the database
        existing_links = await FeedNewsCRUD.get_existing_links([item["link"] for item in feed_items])
        
        # Filter out items that already exist in the database
        new_items = [item for item in feed_items if item["link"] not in existing_links]
        
        if new_items:
            # Insert only the new items (no duplicates)
            await FeedNewsCRUD.create_feed_news_items_bulk(new_items)

        return await FeedURLCRUD.get_feed_url_by_url(normalized_url)

    @staticmethod
    async def update_feed_news_by_url(url: str) -> Optional[FeedURLOut]:
        normalized_url = await FeedURLCRUD.normalize_url(url)

        async with aiohttp.ClientSession() as session:
            feed_data = await FeedParser.fetch_feed(normalized_url, session)
            if not feed_data or hasattr(feed_data, 'bozo_exception'):
                return None

            feed_metadata = FeedParser.parse_feed_metadata(feed_data)
            feed_metadata["url"] = normalized_url
            feed_metadata["domain"] = urlparse(normalized_url).netloc

            feed_items = await FeedParser.parse_feed_items(feed_data, normalized_url, session)

        # Get existing links to filter out already existing news
        existing_links = await FeedNewsCRUD.get_existing_links([item["link"] for item in feed_items])

        # Filter out news items that are already present
        new_items = [item for item in feed_items if item["link"] not in existing_links]

        if new_items:
            await FeedNewsCRUD.create_feed_news_items_bulk(new_items)

        return await FeedURLCRUD.get_feed_url_by_url(normalized_url)

    @staticmethod
    async def get_feed_by_id(feed_id: str):
        # Fetch feed data by its ID from the database
        return await FeedURLCRUD.get_feed_url_by_id(feed_id)

    @staticmethod
    async def get_news_with_feed_info(feed_url: str):
        return await FeedNewsCRUD.get_news_with_feed_info_by_feed_url(feed_url)
        
    @staticmethod
    async def get_feed_with_items_by_id(feed_id: str):
        # Join both collection and read metadata of feed_urls and
        # latest news of feed_news
        feed = await FeedURLCRUD.get_feed_url_by_id(feed_id)
        if not feed:
            return None, []

        items = await FeedNewsCRUD.get_news_items_by_feed_url(feed.url)
        return feed, items

    @staticmethod
    async def get_all_feeds():
        return await FeedURLCRUD.get_all_feed_urls()

    @staticmethod
    async def get_feed_items(feed_url: str, limit: int = 20):
        return await FeedNewsCRUD.get_news_items_by_feed_url(feed_url, limit)
