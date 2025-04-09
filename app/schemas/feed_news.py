from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class FeedNewsCreate(BaseModel):
    feed_url: str

class FeedNewsItem(BaseModel):
    id: str
    title: str
    description: str
    link: str
    pubDate: str
    feed_url: str
    full_content: Optional[str] = None
    is_full_content_fetched: bool = False

    @classmethod
    def from_mongo(cls, item: dict) -> "FeedNewsItem":
        """
        Converts a MongoDB document into a FeedNewsItem instance.
        """
        # MongoDB's _id field is an ObjectId, we convert it to string
        item["id"] = str(item["_id"])  # Convert MongoDB ObjectId to string
        return cls(**item)  # Create an instance of FeedNewsItem using the document data
