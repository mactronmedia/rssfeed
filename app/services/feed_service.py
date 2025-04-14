# services/feed_service.py

import aiohttp
import asyncio
from typing import Optional, List
from urllib.parse import urlparse
from app.core.feed_parser import FeedParser
from app.crud.feed_urls import FeedURLCRUD
from app.crud.feed_news import FeedNewsCRUD
from app.crud.youtube import YouTubeChannelCRUD, YouTubeFeedItemCRUD
from app.schemas.feed_urls import FeedURLOut

class FeedService:
    @staticmethod
    async def add_feed_url(url: str) -> Optional[FeedURLOut]:
        normalized_url = await FeedURLCRUD.normalize_url(url)
        
        existing_feed = await FeedURLCRUD.get_feed_url_by_url(normalized_url)
        if existing_feed:
            return existing_feed

        domain = urlparse(normalized_url).netloc
        existing_domain_feed = await FeedURLCRUD.get_feed_url_by_domain(domain)
        if existing_domain_feed:
            return existing_domain_feed

        async with aiohttp.ClientSession() as session:
            feed_data = await FeedParser.fetch_feed(normalized_url, session)
            if not feed_data or hasattr(feed_data, 'bozo_exception'):
                return None

            feed_metadata = FeedParser.parse_feed_metadata(feed_data)
            feed_metadata["url"] = normalized_url
            feed_metadata["domain"] = domain

            # Insert feed metadata into the database
            await FeedURLCRUD.create_feed_url(feed_metadata)

            # Parse the feed items (news articles)
            feed_items = await FeedParser.parse_feed_items(feed_data, normalized_url, session)

        # Get existing links from the database
        existing_links = await FeedNewsCRUD.get_existing_links([item["link"] for item in feed_items])
        
        # Filter out items that already exist in the database
        new_items = [item for item in feed_items if item["link"] not in existing_links]
        
        if new_items:
            # Insert only the new items (no duplicates)
            await FeedNewsCRUD.create_feed_news_items_bulk(new_items)

        return await FeedURLCRUD.get_feed_url_by_url(normalized_url)

    @staticmethod
    async def update_feed_news_by_url(url: str, session: Optional[aiohttp.ClientSession] = None) -> Optional[FeedURLOut]:
        normalized_url = await FeedURLCRUD.normalize_url(url)

        # Use passed session, or create a new one if missing
        if session is None:
            async with aiohttp.ClientSession() as session:
                return await FeedService.update_feed_news_by_url(url, session)

        feed_data = await FeedParser.fetch_feed(normalized_url, session)
        if not feed_data or hasattr(feed_data, 'bozo_exception'):
            return None

        feed_metadata = FeedParser.parse_feed_metadata(feed_data)
        feed_metadata["url"] = normalized_url
        feed_metadata["domain"] = urlparse(normalized_url).netloc

        feed_items = await FeedParser.parse_feed_items(feed_data, normalized_url, session)

        existing_links = await FeedNewsCRUD.get_existing_links([item["link"] for item in feed_items])
        new_items = [item for item in feed_items if item["link"] not in existing_links]

        if new_items:
            await FeedNewsCRUD.create_feed_news_items_bulk(new_items)

        return await FeedURLCRUD.get_feed_url_by_url(normalized_url)

    @staticmethod
    async def update_all_feeds_concurrently():
        feed_urls = await FeedURLCRUD.get_all_feed_urls()
        if not feed_urls:
            return []

        async with aiohttp.ClientSession() as session:
            tasks = [
                FeedService.update_feed_news_by_url(feed.url, session)
                for feed in feed_urls
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)




    @staticmethod
    async def get_feed_by_id(feed_id: str):
        # Fetch feed data by its ID from the database
        return await FeedURLCRUD.get_feed_url_by_id(feed_id)

    @staticmethod
    async def get_news_with_feed_info(feed_url: str):
        return await FeedNewsCRUD.get_news_with_feed_info_by_feed_url(feed_url)
        
    @staticmethod
    async def get_feed_with_items_by_id(feed_id: str):
        # Join both collection and read metadata of feed_urls and
        # latest news of feed_news
        feed = await FeedURLCRUD.get_feed_url_by_id(feed_id)
        if not feed:
            return None, []

        items = await FeedNewsCRUD.get_news_items_by_feed_url(feed.url)
        return feed, items

    @staticmethod
    async def get_all_feeds():
        return await FeedURLCRUD.get_all_feed_urls()

    @staticmethod
    async def get_feed_items(feed_url: str, limit: int = 20):
        return await FeedNewsCRUD.get_news_items_by_feed_url(feed_url, limit)


    ## Add RSS feeds and YT channel into one sidebar!
    @staticmethod
    async def get_all_sidebar_feeds_combined():
        rss_feeds = await FeedURLCRUD.get_all_feed_urls()
        yt_channels = await YouTubeChannelCRUD.get_all_channels()

        # Normalize into shared format
        combined_feeds = [
            {**feed.dict(), "type": "rss"} for feed in rss_feeds
        ] + [
            {**channel.dict(), "type": "youtube"} for channel in yt_channels
        ]

        # Sort alphabetically by title
        combined_feeds.sort(key=lambda x: x["title"].lower())

        return combined_feeds

 

    @staticmethod
    async def get_combined_feed_items(limit: int = 30) -> List[dict]:
        # Fetch more than needed from both to ensure mix
        rss_items = [item.dict() for item in await FeedNewsCRUD.get_all_news(limit=limit * 2)]
        youtube_items = [item.dict() for item in await YouTubeFeedItemCRUD.get_all_youtube_feed_items(limit=limit * 2)]

        # Tag each item with type
        for item in rss_items:
            item["type"] = "rss"
        for item in youtube_items:
            item["type"] = "youtube"

        # Combine and sort by pubDate
        combined = rss_items + youtube_items
        combined.sort(key=lambda x: x["pubDate"], reverse=True)

        # Return only the first `limit` items
        return combined[:limit]