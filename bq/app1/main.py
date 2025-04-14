# app/main.py
import time

from fastapi import FastAPI, Request
from fastapi.middleware import Middleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.database.mongo_db import connect_to_mongo, close_mongo_connection
from app.api.rss import router as rss_router
from app.core.logger import log_request_completion
from app.routers import web  # Import the new web router



app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Add middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    log_request_completion(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=process_time
    )
    
    return response

# Include routers
app.include_router(web.router)  # New Web UI router for rendering HTML
app.include_router(rss_router, prefix="/api/v1", tags=["rss"])

# CORS middleware (optional but recommended for API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Database event handlers
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

@app.get("/")
async def root():
    return {"message": "RSS Aggregator API"}