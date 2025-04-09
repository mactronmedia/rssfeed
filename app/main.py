from fastapi import FastAPI
from app.api.rss import router as rss_router
from app.database.mongo_db import connect_to_mongo, close_mongo_connection
from app.config import settings

app = FastAPI(title=settings.app_title)

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

app.include_router(rss_router, prefix="/api/v1", tags=["rss"])