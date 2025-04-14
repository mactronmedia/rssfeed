
from app.crud.youtube import YouTubeChannelCRUD
from app.core.youtube_parser import YouTubeFeedParser
from app.schemas.youtube_feed import YouTubeFeedItem, YouTubeFeedResponse, YouTubeChannel

class YouTubeFeedService:
    @staticmethod
    async def fetch_and_save_feed(channel_id: str) -> YouTubeFeedResponse:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        parsed_feed, channel = await YouTubeFeedParser.parse_feed(feed_url)

        if not isinstance(parsed_feed, YouTubeFeedResponse):
            raise ValueError("Failed to parse YouTube feed properly.")

        await YouTubeChannelCRUD.save_youtube_feed_items(parsed_feed.items)
        await YouTubeChannelCRUD.save_youtube_channel(channel)

        return parsed_feed
