from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.crud.feed_urls import FeedURLCRUD
from app.services.feed_service import FeedService
from app.services.article_service import ArticleService
from app.schemas.feed_urls import FeedURLCreate, FeedURLOut
from app.schemas.feed_news import FeedNewsItem

# Define the router once here
router = APIRouter(prefix="/api/v1", tags=["Feeds & News"])

class FeedNewsAPI:
    def __init__(self):
        self._add_routes()

    def _add_routes(self):
        router.add_api_route("/feeds/", FeedNewsAPI.add_feed_url, methods=["POST"], response_model=FeedURLOut, tags=["Feeds"])
        router.add_api_route("/feeds/", FeedNewsAPI.list_feeds, methods=["GET"], response_model=list[FeedURLOut], tags=["Feeds"])
        router.add_api_route("/feeds/items/", FeedNewsAPI.get_feed_items, methods=["GET"], response_model=list[FeedNewsItem], tags=["News Items"])
        router.add_api_route("/articles/", FeedNewsAPI.get_full_article, methods=["GET"], response_model=FeedNewsItem, tags=["Articles"])
        router.add_api_route("/feeds/search/", FeedNewsAPI.search_feed_urls, methods=["GET"], response_model=list[FeedURLOut], tags=["Feeds"])

    @staticmethod
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

    @staticmethod
    async def list_feeds():
        """
        Returns all stored RSS feeds.
        """
        return await FeedService.get_all_feeds()

    @staticmethod
    async def get_feed_items(
        feed_url: str = Query(..., description="URL of the RSS feed"),
        limit: int = Query(20, ge=1, le=100, description="Number of news items (default 20, max 100)")
    ):
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

    @staticmethod
    async def get_full_article(article_link: str = Query(..., description="Link to the article")):
        """
        Returns the full article from the provided link (if available).
        """
        article = await ArticleService.fetch_full_article(article_link)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found.")
        return article

    @staticmethod
    async def search_feed_urls(
        title: Optional[str] = Query(None, description="Search by title"),
        link: Optional[str] = Query(None, description="Search by link"),
        domain: Optional[str] = Query(None, description="Search by domain"),
    ):
        """
        Search feed URLs by title, link, or domain.
        """
        query = {}
        if title:
            query["title"] = {"$regex": title, "$options": "i"}  # Case-insensitive search
        if link:
            query["link"] = {"$regex": link, "$options": "i"}
        if domain:
            query["domain"] = {"$regex": domain, "$options": "i"}

        feeds = await FeedURLCRUD.search_feed_urls(query)
        if not feeds:
            raise HTTPException(status_code=404, detail="No feeds found matching the search criteria.")
        
        return feeds

feed_news_api = FeedNewsAPI()