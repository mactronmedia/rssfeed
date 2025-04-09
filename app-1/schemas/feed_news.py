from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

class FeedNewsItem(BaseModel):
    id: PyObjectId = Field(alias="_id")
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
            from datetime import datetime
            return datetime(*value[:6])
        return value

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True