from typing import Optional, List
from app.database.mongo_db import get_feed_urls_collection
from app.schemas.feed_urls import FeedURLOut

class FeedURLCRUD:
    @staticmethod
    async def create_feed_url(feed_data: dict):
        collection = get_feed_urls_collection()
        result = await collection.insert_one(feed_data)
        return str(result.inserted_id)

    @staticmethod
    async def get_feed_url_by_url(url: str) -> Optional[FeedURLOut]:
        collection = get_feed_urls_collection()
        feed = await collection.find_one({"url": url})
        return FeedURLOut.from_mongo(feed) if feed else None

    @staticmethod
    async def get_all_feed_urls() -> List[FeedURLOut]:
        collection = get_feed_urls_collection()
        feeds = await collection.find().to_list(None)
        return [FeedURLOut.from_mongo(feed) for feed in feeds]

    @staticmethod
    async def update_feed_url(url: str, update_data: dict):
        collection = get_feed_urls_collection()
        await collection.update_one(
            {"url": url},
            {"$set": update_data}
        )

    @staticmethod
    async def get_feed_url_by_domain(domain: str) -> Optional[FeedURLOut]:
        """Check if a feed from this domain already exists"""
        collection = get_feed_urls_collection()
        feed = await collection.find_one({"domain": domain})
        return FeedURLOut.from_mongo(feed) if feed else None

    @staticmethod
    async def search_feed_urls(query: dict) -> List[FeedURLOut]:
        collection = get_feed_urls_collection()
        feeds = await collection.find(query).to_list(None)
        return [FeedURLOut.from_mongo(feed) for feed in feeds]
        
    @staticmethod
    async def normalize_url(url: str) -> str:
        """Normalize URL to prevent duplicates with different formats"""
        url = url.strip()
        if url.endswith('/'):
            url = url[:-1]
        return url.lower()        