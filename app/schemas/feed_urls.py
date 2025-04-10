# schemas/feed_urls.py

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class FeedURLCreate(BaseModel):
    url: str

class FeedURLOut(BaseModel):
    id: str = Field(alias="_id")
    title: str
    description: str
    link: str
    image: str
    pubDate: datetime
    last_updated: datetime
    domain: str
    url: str  
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

    @classmethod
    def from_mongo(cls, data: dict):
        if not data:
            return data
        id = data.pop('_id', None)
        return cls(**dict(data, id=str(id)))