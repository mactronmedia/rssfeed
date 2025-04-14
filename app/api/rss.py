# api/rss.py
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, status

from app.services.feed_service import FeedService
from app.services.article_service import ArticleService
from app.services.youtube import YouTubeFeedService
from app.services.scheduler import Update

from app.schemas.feed_urls import FeedURLOut
from app.schemas.feed_news import FeedNewsItem
from app.schemas.youtube_feed import YouTubeFeedResponse
router = APIRouter(tags=["Feeds & News"])

# --- News Feeds --- #

@router.get("/feeds/", response_model=FeedURLOut, tags=["Feeds"])
async def add_feed_url(url: str = Query(..., description="RSS feed URL")):
    feed_url = await FeedService.add_feed_url(url)
    if not feed_url:
        raise HTTPException(status_code=400, detail="Invalid RSS feed URL or unable to parse feed")
    return feed_url


@router.get("/feeds/items/", response_model=List[FeedNewsItem], tags=["News Items"])
async def get_feed_items(
    feed_url: str = Query(..., description="RSS feed URL"),
    limit: int = Query(20, ge=1, le=100, description="Number of news items")
):
    items = await FeedService.get_feed_items(feed_url, limit)
    if not items:
        raise HTTPException(status_code=404, detail="RSS feed not found or contains no items.")
    return items


@router.get("/feeds/with-items/", response_model=dict, tags=["Feeds"])
async def add_and_fetch_items(
    url: str = Query(..., description="RSS feed URL"),
    limit: int = Query(20, ge=1, le=100, description="Number of news items")
):
    feed_url = await FeedService.add_feed_url(url)
    if not feed_url:
        raise HTTPException(status_code=400, detail="Invalid RSS feed URL or unable to parse feed")

    items = await FeedService.get_feed_items(url, limit)
    if not items:
        raise HTTPException(status_code=404, detail="RSS feed found, but contains no items.")

    return {"feed": feed_url, "items": items}


@router.get("/feeds/update/", response_model=FeedURLOut, tags=["Feeds"])
async def update_feed_by_url(url: str = Query(..., description="RSS feed URL")):
    updated_feed = await FeedService.update_feed_news_by_url(url)
    if not updated_feed:
        raise HTTPException(status_code=400, detail="Failed to update feed news from URL.")
    return updated_feed


@router.get("/feeds/search/", response_model=List[FeedURLOut], tags=["Feeds"])
async def search_feed_urls(
    title: Optional[str] = Query(None, description="Search by title"),
    link: Optional[str] = Query(None, description="Search by link"),
    domain: Optional[str] = Query(None, description="Search by domain")
):
    feeds = await FeedService.search_feed_urls(title, link, domain)
    if not feeds:
        raise HTTPException(status_code=404, detail="No feeds found matching the search criteria.")
    return feeds


@router.get("/feeds/update-all/", response_model=dict, tags=["Feeds"])
async def update_all_feeds_periodically(
    background_tasks: BackgroundTasks,
    interval_min: int = Query(5, ge=1, le=60, description="Interval in minutes")
):
    background_tasks.add_task(Update.periodic_feed_updater, interval_min)
    return {"status": "started", "message": f"Feed updates scheduled every {interval_min} minutes"}


# --- Articles --- #

@router.get("/articles/", response_model=FeedNewsItem, tags=["Articles"])
async def get_full_article(
    article_link: str = Query(..., description="Link to the article")
):
    article = await ArticleService.fetch_full_article(article_link)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    return article


# --- YouTube --- #

@router.get("/feeds/youtube/", response_model=YouTubeFeedResponse, tags=["YouTube Feeds"])
async def get_youtube_feed(
    channel_id: str = Query(..., description="YouTube Channel ID")
):
    try:
        return await YouTubeFeedService.fetch_and_save_feed(channel_id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
