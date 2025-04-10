from fastapi.responses import HTMLResponse
from fastapi import APIRouter, Request, HTTPException
from app.crud.feed_news import FeedNewsCRUD
from app.services.feed_service import FeedService
from fastapi.templating import Jinja2Templates

# Initialize the router and templates
router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render index page with all feeds (left sidebar) and latest news (center).
    """
    try:
        feeds = await FeedService.get_all_feeds()
        latest_news = await FeedNewsCRUD.get_all_news(limit=30)  # show latest 30
        return templates.TemplateResponse("index.html", {"request": request, "feeds": feeds, "news": latest_news})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# All News from All Feeds
@router.get("/all-news", response_class=HTMLResponse)
async def get_all_news(request: Request):
    """
    Render a page with all news items from all feeds.
    """
    try:
        # Fetch all news items from the database, with feed information included
        all_news = await FeedNewsCRUD.get_all_news_with_feed_info()

        if not all_news:
            raise HTTPException(status_code=404, detail="No news found.")

        return templates.TemplateResponse("all_news.html", {"request": request, "news": all_news})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to list all RSS feeds
@router.get("/feeds", response_class=HTMLResponse)
async def list_feeds(request: Request):
    """
    Render a page with the list of all RSS feeds.
    """
    try:
        feeds = await FeedService.get_all_feeds()
        if not feeds:
            raise HTTPException(status_code=404, detail="No feeds found.")
        return templates.TemplateResponse("list_feeds.html", {"request": request, "feeds": feeds})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route to get feed details by feed_id
@router.get("/feed/{feed_id}", response_class=HTMLResponse)
async def get_feed_by_id(request: Request, feed_id: str):
    """
    Render a page with the details of a specific RSS feed and associated news items.
    """
    try:
        # Fetch the feed by ID
        feed = await FeedService.get_feed_by_id(feed_id)
        if not feed:
            raise HTTPException(status_code=404, detail="Feed not found")
        
        # Fetch the news items for the feed
        items_with_feed = await FeedService.get_news_with_feed_info(feed.url)
        return templates.TemplateResponse("feed_detail.html", {
            "request": request,
            "feed": feed,
            "items": items_with_feed
        })
    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions
    except Exception as e:
        # Catch any unexpected errors and raise a 500
        raise HTTPException(status_code=500, detail=str(e))
