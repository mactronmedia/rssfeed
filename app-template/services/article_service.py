from typing import Optional
from app.core.article_parser import ArticleParser
from app.crud.feed_news import FeedNewsCRUD
from app.schemas.feed_news import FeedNewsItem

class ArticleService:
    @staticmethod
    async def fetch_full_article(link: str) -> Optional[FeedNewsItem]:
        # Check if article already has full content
        news_item = await FeedNewsCRUD.get_news_item_by_link(link)
        if not news_item:
            return None
            
        if news_item.is_full_content_fetched:
            return news_item

        # Fetch full content
        full_content = await ArticleParser.fetch_full_content(link)
        if not full_content:
            return None

        # Update the news item
        await FeedNewsCRUD.update_news_item(link, {
            "full_content": full_content,
            "is_full_content_fetched": True
        })

        return await FeedNewsCRUD.get_news_item_by_link(link)