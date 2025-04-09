from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.services.feed_service import FeedService
from app.services.article_service import ArticleService
from app.schemas.feed_urls import FeedURLOut
from app.schemas.feed_news import FeedNewsOut

router = APIRouter()

@router.post("/feeds/", response_model=FeedURLOut)
async def add_feed_url(url: str):
    try:
        return await FeedService.add_feed_url(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/feeds/", response_model=List[FeedURLOut])
async def list_feeds(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    return await FeedService.get_all_feeds(skip, limit)

@router.get("/feeds/{feed_url}/items", response_model=List[FeedNewsOut])
async def get_feed_items(
    feed_url: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    items = await FeedService.get_feed_items(feed_url, skip, limit)
    if not items:
        raise HTTPException(status_code=404, detail="Feed not found or has no items")
    return items

@router.get("/articles/{article_id}", response_model=FeedNewsOut)
async def get_full_article(article_id: str):
    article = await ArticleService.fetch_full_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article