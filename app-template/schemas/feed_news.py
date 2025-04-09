from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from bson import ObjectId

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

    @field_validator('pubDate', mode='before')
    def parse_pubdate(cls, value):
        if isinstance(value, list):
            # Convert feedparser time tuple to datetime
            return datetime(*value[:6])
        return value

    @classmethod
    def from_mongo(cls, data: dict):
        """Convert MongoDB document to Pydantic model"""
        if not data:
            return None
        
        # Convert ObjectId to string
        if '_id' in data:
            data['_id'] = str(data['_id'])
            
        # Handle datetime conversion if needed
        if 'pubDate' in data and isinstance(data['pubDate'], list):
            data['pubDate'] = datetime(*data['pubDate'][:6])
            
        return cls(**data)

    class Config:
        from_attributes = True
        populate_by_name = True