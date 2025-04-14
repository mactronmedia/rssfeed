# api/rss.py

import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, status
from app.services.feed_service import FeedService
from app.services.article_service import ArticleService
from app.schemas.feed_urls import FeedURLOut
from app.schemas.feed_news import FeedNewsItem
from app.crud.feed_urls import FeedURLCRUD
from app.crud.youtube_feed import YouTubeFeedService


from app.core.youtube_parser import YouTubeFeedParser
from app.schemas.youtube_feed import YouTubeFeedItem, YouTubeFeedResponse, YouTubeChannel


router = APIRouter(tags=["Feeds & News"])

@router.get("/feeds/", response_model=list[FeedURLOut], tags=["Feeds"])
async def list_feeds():
    return await FeedService.get_all_feeds()

@router.post("/feeds/", response_model=FeedURLOut, tags=["Feeds"])
async def add_feed_url(url: str):
    feed_service = FeedService()
    feed_url = await feed_service.add_feed_url(url)
    if not feed_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid RSS feed URL or unable to parse feed"
        )
    return feed_url

@router.get("/feeds/items/", response_model=list[FeedNewsItem], tags=["News Items"])
async def get_feed_items(
    feed_url: str = Query(..., description="URL of the RSS feed"),
    limit: int = Query(20, ge=1, le=100, description="Number of news items (default 20, max 100)")
):
    items = await FeedService.get_feed_items(feed_url, limit)
    if not items:
        raise HTTPException(status_code=404, detail="RSS feed not found or contains no items.")
    return items


@router.get("/articles/", response_model=FeedNewsItem, tags=["Articles"])
async def get_full_article(article_link: str = Query(..., description="Link to the article")):
    article = await ArticleService.fetch_full_article(article_link)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    return article


@router.get("/feeds/with-items/", response_model=dict, tags=["Feeds"])
async def add_and_fetch_items(
    url: str = Query(..., description="URL of the RSS feed"),
    limit: int = Query(20, ge=1, le=100, description="Number of news items to fetch")
):
    feed_service = FeedService()

    feed_url = await feed_service.add_feed_url(url)
    if not feed_url:
        raise HTTPException(status_code=400, detail="Invalid RSS feed URL or unable to parse feed")

    items = await FeedService.get_feed_items(url, limit)
    if not items:
        raise HTTPException(status_code=404, detail="RSS feed found, but contains no items.")

    return {"feed": feed_url, "items": items}


@router.get("/feeds/update/", response_model=FeedURLOut, tags=["Feeds"])
async def update_feed_by_url(url: str):
    feed_service = FeedService()
    updated_feed = await feed_service.update_feed_news_by_url(url)
    if not updated_feed:
        raise HTTPException(status_code=400, detail="Failed to update feed news from URL.")
    return updated_feed


@router.get("/feeds/search/", response_model=list[FeedURLOut], tags=["Feeds"])
async def search_feed_urls(
    title: Optional[str] = Query(None, description="Search by title"),
    link: Optional[str] = Query(None, description="Search by link"),
    domain: Optional[str] = Query(None, description="Search by domain")
):
    query = {}
    if title:
        query["title"] = {"$regex": title, "$options": "i"}
    if link:
        query["link"] = {"$regex": link, "$options": "i"}
    if domain:
        query["domain"] = {"$regex": domain, "$options": "i"}

    feeds = await FeedURLCRUD.search_feed_urls(query)
    if not feeds:
        raise HTTPException(status_code=404, detail="No feeds found matching the search criteria.")
    return feeds


@router.get("/feeds/update-all/", response_model=dict, tags=["Feeds"])
async def update_all_feeds_periodically(background_tasks: BackgroundTasks, interval_min: int = 5):
    background_tasks.add_task(periodic_feed_updater, interval_min)
    return {"status": "started", "message": f"Feed updates scheduled every {interval_min} minutes"}


async def periodic_feed_updater(interval_min: int):
    while True:
        try:
            print(f"[FeedUpdater] Starting update cycle (every {interval_min} min)")
            results = await FeedService.update_all_feeds_concurrently()

            for result in results:
                if isinstance(result, Exception):
                    print(f"[FeedUpdater] Error during feed update: {result}")
                elif result:
                    print(f"[FeedUpdater] Updated feed: {result.url}")
                else:
                    print(f"[FeedUpdater] Skipped or failed feed")
        except Exception as e:
            print(f"[FeedUpdater] Fatal error in periodic updater: {e}")

        await asyncio.sleep(interval_min * 60)



@router.get("/feeds/youtube/", response_model=YouTubeFeedResponse, tags=["YouTube Feeds"])
async def get_youtube_feed(channel_id: str = Query(..., description="YouTube Channel ID")):
    try:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        
        # Unpacking the tuple returned from `parse_feed`
        parsed_feed, channel = await YouTubeFeedParser.parse_feed(feed_url)

        # Ensure that parsed_feed is an instance of YouTubeFeedResponse
        if not isinstance(parsed_feed, YouTubeFeedResponse):
            raise HTTPException(status_code=500, detail="Failed to parse YouTube feed properly.")

        # Save to DB
        await YouTubeFeedService.save_youtube_feed_items(parsed_feed.items)
        await YouTubeFeedService.save_youtube_channel(channel)  # Save the channel information

        return parsed_feed

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
