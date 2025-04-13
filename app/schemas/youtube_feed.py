# schemas/youtube_feed.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class YouTubeFeedItem(BaseModel):
    title: str
    link: str
    pubDate: datetime
    thumbnail: str
    channel_id: Optional[str] = None
    fetched_at: datetime = datetime.utcnow()

class YouTubeFeedResponse(BaseModel):
    items: List[YouTubeFeedItem]
    channel_id: str
    fetched_at: str