from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl

class ArticleContentModel(BaseModel):
    raw: str
    summary: Optional[str] = None

class ArticleModel(BaseModel):
    feed_id: str = Field(..., description="Reference to feeds collection")
    title: str
    url: HttpUrl
    published_at: datetime
    author: Optional[str] = None
    summary: Optional[str] = None
    content: ArticleContentModel
    language: Optional[str] = None
    tags: Optional[List[str]] = None
    image_url: Optional[HttpUrl] = None

    class Config:
        schema_extra = {
            "example": {
                "feed_id": "507f1f77bcf86cd799439011",
                "title": "Breaking News on Linux",
                "url": "https://example.com/article/1",
                "published_at": "2025-04-14T09:30:00Z",
                "author": "John Doe",
                "summary": "This article talks about...",
                "content": {
                    "raw": "<original HTML>",
                    "summary": "Short summary or AI-generated summary"
                },
                "language": "en",
                "tags": ["linux", "open-source"],
                "image_url": "https://example.com/image.jpg"
            }
        }