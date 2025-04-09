from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Optional

class FeedNewsCreate(BaseModel):
    feed_url: str

class FeedNewsItem(BaseModel):
    id: str = Field(alias="_id")
    title: str
    description: str
    link: str
    pubDate: datetime
    media_thumbnail: str = ""
    feed_url: str
    full_content: str = ""
    is_full_content_fetched: bool = False

    '''
    @field_validator('pubDate', mode='before')
    def parse_pubdate(cls, value):
        if isinstance(value, list):
            return datetime(*value[:6])
        return value
    '''

    @classmethod
    def from_mongo(cls, data: dict):
        if not data:
            return None
        id = data.pop('_id', None)
        return cls(**dict(data, id=str(id)))