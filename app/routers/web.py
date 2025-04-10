from fastapi.responses import HTMLResponse
from fastapi import APIRouter, Request, HTTPException
from app.services.feed_service import FeedService
from app.schemas.feed_urls import FeedURLOut
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/web", tags=["Web"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/feeds", response_class=HTMLResponse)
async def list_feeds(request: Request):
    """
    Render a page with the list of all RSS feeds.
    """
    feeds = await FeedService.get_all_feeds()
    if not feeds:
        raise HTTPException(status_code=404, detail="No feeds found.")
    return templates.TemplateResponse("list_feeds.html", {"request": request, "feeds": feeds})

'''
@router.get("/feed/{feed_id}", response_class=HTMLResponse)
async def get_feed_by_id(request: Request, feed_id: str):
    # Fetch the feed by ID using the service method
    # http://localhost:8000/web/feed/67f63d499efb47e5229f196e

    feed = await FeedService.get_feed_by_id(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return templates.TemplateResponse("feed_detail.html", {"request": request, "feed": feed})
'''

@router.get("/feed/{feed_id}", response_class=HTMLResponse)
async def get_feed_by_id(request: Request, feed_id: str):
    feed = await FeedService.get_feed_by_id(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    items_with_feed = await FeedService.get_news_with_feed_info(feed.url)
    return templates.TemplateResponse("feed_detail.html", {
        "request": request,
        "feed": feed,
        "items": items_with_feed
    })
