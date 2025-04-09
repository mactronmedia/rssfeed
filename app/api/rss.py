from fastapi import APIRouter, HTTPException, Query
from app.services.feed_service import FeedService
from app.services.article_service import ArticleService
from app.schemas.feed_urls import FeedURLCreate, FeedURLOut
from app.schemas.feed_news import FeedNewsItem

router = APIRouter(prefix="/api/v1", tags=["Feeds & News"])

@router.post("/feeds/", response_model=FeedURLOut, tags=["Feeds"])
async def add_feed_url(feed: FeedURLCreate):
    """
    Add a new RSS feed. Returns an error if the feed already exists or is invalid.
    """
    result = await FeedService.add_feed_url(feed.url)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Invalid RSS feed URL or unable to fetch feed data."
        )
    return result

@router.get("/feeds/", response_model=list[FeedURLOut], tags=["Feeds"])
async def list_feeds():
    """
    Returns all stored RSS feeds.
    """
    return await FeedService.get_all_feeds()

@router.get("/feeds/items/", response_model=list[FeedNewsItem], tags=["News Items"])
async def get_feed_items(
    feed_url: str = Query(..., description="URL of the RSS feed"),
    limit: int = Query(20, ge=1, le=100, description="Number of news items (default 20, max 100)")):
    """
    Returns news items from the specified RSS feed.
    """
    items = await FeedService.get_feed_items(feed_url, limit)
    if not items:
        raise HTTPException(
            status_code=404,
            detail="RSS feed not found or contains no items."
        )
    return items

@router.get("/articles/", response_model=FeedNewsItem, tags=["Articles"])
async def get_full_article(article_link: str = Query(..., description="Link to the article")):
    """
    Returns the full article from the provided link (if available).
    """
    article = await ArticleService.fetch_full_article(article_link)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    return article
