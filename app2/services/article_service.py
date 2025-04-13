# services/article_service.py

from typing import Optional
from app.core.article_parser import ArticleParser
from app.crud.feed_news import FeedNewsCRUD
from app.schemas.feed_news import FeedNewsItem

class ArticleService:
    @staticmethod
    async def fetch_full_article(link: str) -> Optional[FeedNewsItem]:
        """
        Fetches the full article content for the given news item link.
        
        Returns:
            FeedNewsItem: The news item with full content if successful, else None.
        """
        # Check if article already has full content fetched
        news_item = await FeedNewsCRUD.get_news_item_by_link(link)
        if not news_item:
            return None  # Article not found in database

        if news_item.is_full_content_fetched:
            return news_item  # Return article if full content already fetched

        # Fetch the full content if not fetched previously
        full_content = await ArticleParser.fetch_full_content(link)
        if not full_content:
            return None  # Return None if content fetching failed

        # Update the news item with full content
        await FeedNewsCRUD.update_news_item(link, {
            "full_content": full_content,
            "is_full_content_fetched": True
        })

        # Return the updated news item with full content
        return await FeedNewsCRUD.get_news_item_by_link(link)
