# crud/youtube_chanyoutube.py

from typing import List
from pymongo.errors import BulkWriteError

from app.database.mongo_db import get_youtube_feed_collection, get_youtube_channel_collection
from app.schemas.youtube_feed import YouTubeFeedItem, YouTubeChannel


class YouTubeChannelCRUD:
    @staticmethod
    async def get_all_channels():
        collection = get_youtube_channel_collection()
        channels = await collection.find().sort("title", 1).to_list(None)
        return [YouTubeChannel.from_mongo(channel) for channel in channels]

    @staticmethod
    async def save_youtube_channel(channel: YouTubeChannel):
        try:
            collection = get_youtube_channel_collection()
            existing_channel = await collection.find_one({"channel_id": channel.channel_id})

            if existing_channel:
                await collection.update_one(
                    {"channel_id": channel.channel_id},
                    {"$set": channel.dict()}
                )
            else:
                await collection.insert_one(channel.dict())

            print(f"Channel {channel.title} saved/updated successfully.")
        except Exception as e:
            print(f"[Mongo] Failed to save YouTube channel: {e}")

    @staticmethod
    async def save_youtube_feed_items(items: List[YouTubeFeedItem]):
        documents = [item.dict() for item in items]
        if not documents:
            return

        try:
            await get_youtube_feed_collection().insert_many(documents, ordered=False)
        except BulkWriteError as e:
            print(f"[Mongo] Bulk insert error: {e.details}")
        except Exception as e:
            print(f"[Mongo] Insert failed: {e}")

    @staticmethod
    async def get_all_youtube_feed_items(limit: int = 30) -> List[YouTubeFeedItem]:
        collection = get_youtube_feed_collection()
        items = await collection.find().sort("pubDate", -1).limit(limit).to_list(limit)
        return [YouTubeFeedItem(**item) for item in items]