from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from app.services.feed_service import FeedService
from app.services.article_service import ArticleService
from app.schemas.feed_urls import FeedURLOut  # Update this import
from app.schemas.feed_news import FeedNewsItem  # Update this import

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def home(request: Request):
    feeds = await FeedService.get_all_feeds()
    news_items = await FeedService.get_latest_news(limit=12)
    return templates.TemplateResponse("home.html", {
        "request": request,
        "feeds": feeds,
        "news_items": news_items,
        "active_feed": None
    })

@router.post("/feeds")
async def add_feed(request: Request):
    form_data = await request.form()
    url = form_data.get("url")
    if url:
        feed = await FeedService.add_feed_url(url)
    feeds = await FeedService.get_all_feeds()
    return templates.TemplateResponse("partials/feed_item.html", {
        "request": request,
        "feed": feed,
        "active_feed": None
    })

@router.get("/feeds/{feed_id}/news")
async def get_feed_news(feed_id: str, request: Request):
    news_items = await FeedService.get_news_items_by_feed_id(feed_id, limit=12)
    feed = await FeedService.get_feed_by_id(feed_id)
    return templates.TemplateResponse("partials/news_item.html", {
        "request": request,
        "item": news_items
    })

@router.get("/articles/{article_id}/full")
async def get_full_article(article_id: str, request: Request):
    article = await ArticleService.get_full_article(article_id)
    return templates.TemplateResponse("partials/full_article.html", {
        "request": request,
        "article": article
    })