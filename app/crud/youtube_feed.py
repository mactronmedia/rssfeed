# crud/youtube_feed.py

from app.database.mongo_db import get_youtube_feed_collection
from app.schemas.youtube_feed import YouTubeFeedItem
from typing import List

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