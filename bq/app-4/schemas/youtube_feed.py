# schemas/youtube_feed.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class YouTubeChannel(BaseModel):
    id: str = Field(alias="_id")  # Converting _id to id
    title: str
    link: str
    description: Optional[str] = ""
    image: str  # YouTube Channel Thumbnail
    published: datetime
    fetched_at: datetime

    @classmethod
    def from_mongo(cls, mongo_document: dict) -> "YouTubeChannel":
        if "_id" in mongo_document:
            mongo_document["_id"] = str(mongo_document["_id"])  # Ensure ObjectId is converted to string
        return cls(**mongo_document)

class YouTubeFeedItem(BaseModel):
    title: str
    link: str
    pubDate: datetime
    thumbnail: str
    channel_id: Optional[str] = None
    fetched_at: datetime = datetime.utcnow()

class YouTubeFeedResponse(BaseModel):
    items: List[YouTubeFeedItem]
    _id: str
    fetched_at: str
