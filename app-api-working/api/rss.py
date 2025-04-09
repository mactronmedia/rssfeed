from fastapi import APIRouter, HTTPException
from app.services.feed_service import FeedService
from app.services.article_service import ArticleService
from app.schemas.feed_urls import FeedURLCreate, FeedURLOut
from app.schemas.feed_news import FeedNewsItem

router = APIRouter()

@router.post("/feeds/", response_model=FeedURLOut)
async def add_feed_url(feed: FeedURLCreate):
    result = await FeedService.add_feed_url(feed.url)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid RSS feed URL")
    return result

@router.get("/feeds/", response_model=list[FeedURLOut])
async def list_feeds():
    return await FeedService.get_all_feeds()

@router.get("/feeds/{feed_url}/items", response_model=list[FeedNewsItem])
async def get_feed_items(feed_url: str, limit: int = 20):
    items = await FeedService.get_feed_items(feed_url, limit)
    if not items:
        raise HTTPException(status_code=404, detail="Feed not found or no items available")
    return items

@router.get("/articles/{article_link}", response_model=FeedNewsItem)
async def get_full_article(article_link: str):
    article = await ArticleService.fetch_full_article(article_link)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article