from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class FeedNewsCreate(BaseModel):
    feed_url: str

class FeedNewsItem(BaseModel):
    id: str = Field(alias="_id")
    title: str
    description: str
    link: str
    pubDate: datetime
    media_thumbnail: str
    feed_url: str
    full_content: Optional[str] = None
    is_full_content_fetched: bool

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }
