from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.crud.feed_news import FeedNewsCRUD
from app.services.feed_service import FeedService

# Initialize the router and templates
router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


async def fetch_data_for_page():
    """
    Helper function to gather all necessary data for the index page.
    """
    try:
        feeds = await FeedService.get_all_feeds()
        latest_news = await FeedNewsCRUD.get_all_news(limit=20)
        return {"feeds": feeds, "news": latest_news}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render index page with all feeds (left sidebar) and latest news (center).
    """
    context = await fetch_data_for_page()
    return templates.TemplateResponse("index.html", {**context, "request": request})


@router.get("/latest-news", response_class=HTMLResponse)
async def get_latest_news(request: Request):
    """
    Returns just the news list HTML for AJAX updates.
    """
    context = await fetch_data_for_page()
    return templates.TemplateResponse("components/news_list.html", {**context, "request": request})







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
        # Fetch all feeds to display in the sidebar
        feeds = await FeedService.get_all_feeds()

        return templates.TemplateResponse("components/feed_detail.html", {
            "request": request,
            "feed": feed,
            "items": items_with_feed,
            "feeds": feeds  # Pass all feeds for the sidebar
        })
    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
