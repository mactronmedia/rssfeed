from typing import List, Optional
from app.database.mongo_db import get_feed_news_collection
from app.schemas.feed_news import FeedNewsItem

class FeedNewsCRUD:
    @staticmethod
    async def create_feed_news_item(news_item: dict):
        collection = get_feed_news_collection()
        result = await collection.insert_one(news_item)
        return str(result.inserted_id)

    @staticmethod
    async def get_news_items_by_feed_url(feed_url: str, limit: int = 20) -> List[FeedNewsItem]:
        collection = get_feed_news_collection()
        items = await collection.find({"feed_url": feed_url}).sort("pubDate", -1).limit(limit).to_list(limit)
        return [FeedNewsItem.from_mongo(item) for item in items]

    @staticmethod
    async def get_news_item_by_link(link: str) -> Optional[FeedNewsItem]:
        collection = get_feed_news_collection()
        item = await collection.find_one({"link": link})
        return FeedNewsItem.from_mongo(item) if item else None

    @staticmethod
    async def update_news_item(link: str, update_data: dict):
        collection = get_feed_news_collection()
        await collection.update_one(
            {"link": link},
            {"$set": update_data}
        )

    @staticmethod
    async def get_existing_links(links: List[str]) -> set:
        collection = get_feed_news_collection()
        existing_items = await collection.find(
            {"link": {"$in": links}},
            projection={"link": 1}
        ).to_list(None)
        return {item["link"] for item in existing_items}

    @staticmethod
    async def create_feed_news_items_bulk(news_items: List[dict]):
        if not news_items:
            return
        collection = get_feed_news_collection()
        result = await collection.insert_many(news_items)
        return result.inserted_ids
