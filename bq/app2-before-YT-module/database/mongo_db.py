from app.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

class Database:
    client: AsyncIOMotorClient = None

db = Database()

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.mongo_url)
    print("Connected to MongoDB")

async def close_mongo_connection():
    db.client.close()
    print("Disconnected from MongoDB")

def get_db():
    return db.client[settings.mongo_db_name]

def get_feed_urls_collection():
    return get_db().feed_urls

def get_feed_news_collection():
    return get_db().feed_news