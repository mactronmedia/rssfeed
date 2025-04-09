from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.templating import Jinja2Templates
from app.services.feed_service import FeedService
from app.services.article_service import ArticleService
from app.crud.feed_urls import FeedURLCRUD
from app.crud.feed_news import FeedNewsCRUD

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse("feeds.html", {
        "request": request,
        "feeds": await FeedURLCRUD.get_all_feed_urls()
    })

@router.get("/add-feed")
async def show_add_feed_form(request: Request):
    return templates.TemplateResponse("add_feed.html", {"request": request})

@router.post("/add-feed")
async def add_feed(request: Request, url: str = Form(...)):
    feed = await FeedService.add_feed_url(url)
    if not feed:
        return templates.TemplateResponse("add_feed.html", {
            "request": request,
            "error": "Invalid RSS feed URL"
        })
    return templates.TemplateResponse("add_feed.html", {
        "request": request,
        "success": f"Feed '{feed.title}' added successfully"
    })

@router.get("/feeds")
async def list_feeds(request: Request):
    feeds = await FeedURLCRUD.get_all_feed_urls()
    return templates.TemplateResponse("feeds.html", {
        "request": request,
        "feeds": feeds
    })

@router.get("/feed/{feed_id}/items")
async def show_feed_items(request: Request, feed_id: str):
    try:
        feed = await FeedURLCRUD.get_feed_url_by_id(feed_id)
        if not feed:
            raise HTTPException(status_code=404, detail="Feed not found")
        
        items = await FeedNewsCRUD.get_news_items_by_feed_url(feed.url)
        
        # Convert items to dict for template
        items_dict = []
        for item in items:
            item_dict = item.model_dump()
            item_dict["pubDate"] = item.pubDate  # Ensure datetime is properly handled
            items_dict.append(item_dict)
        
        return templates.TemplateResponse("feed_items.html", {
            "request": request,
            "feed": feed.model_dump(),
            "items": items_dict
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest-news")
async def show_latest_news(request: Request, limit: int = 20):
    try:
        items = await FeedNewsCRUD.get_latest_news(limit)
        
        # Enhance items with feed information
        enhanced_items = []
        for item in items:
            item_dict = item.model_dump()
            feed = await FeedURLCRUD.get_feed_url_by_url(item.feed_url)
            if feed:
                item_dict["feed_title"] = feed.title
                item_dict["feed_image"] = feed.image
            enhanced_items.append(item_dict)
        
        return templates.TemplateResponse("latest_news.html", {
            "request": request,
            "items": enhanced_items
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/article/{article_id}")
async def show_full_article(request: Request, article_id: str):
    article = await ArticleService.fetch_full_article(article_id)
    return templates.TemplateResponse("article.html", {
        "request": request,
        "article": article
    })