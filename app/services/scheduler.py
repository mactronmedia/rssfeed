import asyncio
from app.services.feed_service import FeedService

class Update():
    @staticmethod
    async def periodic_feed_updater(interval_min: int):
        while True:
            try:
                print(f"[FeedUpdater] Starting update cycle (every {interval_min} min)")
                results = await FeedService.update_all_feeds_concurrently()

                for result in results:
                    if isinstance(result, Exception):
                        print(f"[FeedUpdater] Error during feed update: {result}")
                    elif result:
                        print(f"[FeedUpdater] Updated feed: {result.url}")
                    else:
                        print(f"[FeedUpdater] Skipped or failed feed")
            except Exception as e:
                print(f"[FeedUpdater] Fatal error in periodic updater: {e}")

            await asyncio.sleep(interval_min * 60)
