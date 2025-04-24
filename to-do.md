I'm working on RSS aggregator like Inoreader with FastAPI and MongoDB. The app have 4 MongoDB collections:

MongoDB collections:

- feeds // Stored all medata from news, youtube, podcast
- news_articles // Full articles with all details
- youtube_videos // Embed videos with all details
- podcast_episodes // Audio file with all details

- feeds

{
  "_id": ObjectId("..."),
  "title": "My Tech Feed",  // Name of the feed (required)
  "description": "Tech news and updates",  // Brief description of the feed
  "feed_url": "https://rss.example.com/feed.xml",  // Feed URL (required, unique)
  "type": "news", // Type of feed: news, video, podcast
  "site_url": "example.com",  // Domain (unique)
  "favicon": "https://example.com/favicon.ico",  // Favicon URL
  "language": "en",  // Language of the feed (ISO 639-1)
  "category": ["technology", "linux"],  // Categories associated with the feed
  "last_fetched": ISODate("2025-04-14T09:30:00Z"),  // Last time the feed was fetched
  "is_active": true,  // Flag to indicate if the feed is active or not
  "parse_interval": 5,  // How often to parse (e.g., integer in minutes)
}

- news_articles

{
  "_id": ObjectId("..."),
  "feed_id": ObjectId("..."),  // Reference to feeds collection (required)
  "title": "Breaking News on Linux",  // Article title (required)
  "url": "https://example.com/article/1",  // URL to the article (required)
  "published_at": ISODate("2025-04-14T09:30:00Z"),  // Publish timestamp
  "author": "John Doe",  // Author of the article (optional)
  "summary": "This article talks about...",  // A brief summary (optional)
  "content": {  // Full content of the article
    "raw": "<original HTML>",  // Raw HTML (for future processing or display)
    "summary": "Short summary or AI-generated summary"  // Optional AI-generated summary
  },
  "language": "en",  // Language of the article (optional but recommended)
  "tags": ["linux", "open-source"],  // Tags for better filtering (optional)
  "image_url": "https://example.com/image.jpg"  // Optional featured image
}

- youtube_videos

{
  "_id": ObjectId("..."),
  "feed_id": ObjectId("..."),  // Reference to feeds collection (required)
  "video_id": "abc123",  // YouTube video ID (required)
  "title": "Learn Linux Basics",  // Video title (required)
  "channel_id": "UCxyz123",  // YouTube channel ID (required)
  "published_at": ISODate("2025-04-14T09:30:00Z"),  // Publish timestamp
  "description": "This video covers the basics of Linux",  // Video description
  "thumbnail_url": "https://example.com/thumbnail.jpg",  // Video thumbnail URL
  "embed_url": "https://www.youtube.com/embed/abc123",  // URL for embedding
  "duration": "00:15:30",  // Duration of the video
  "tags": ["linux", "tutorial"]  // Tags for categorization
}


- podcast_episodes

{
  "_id": ObjectId("..."),
  "feed_id": ObjectId("..."),  // Reference to feeds collection (required)
  "episode_id": "ep123",  // Unique episode ID (required)
  "title": "The Future of Linux",  // Episode title (required)
  "audio_url": "https://example.com/audio/ep123.mp3",  // Audio file URL (required)
  "published_at": ISODate("2025-04-14T09:30:00Z"),  // Publish timestamp
  "description": "In this episode, we discuss the future of Linux",  // Episode description
  "duration": "00:45:00",  // Duration in hh:mm:ss
  "episode_number": 42,  // Episode number (optional)
  "enclosure_type": "audio/mpeg",  // Type of audio file (optional)
  "tags": ["linux", "podcast"]  // Tags for categorization
}

Features:

Use async and classes!

rss/
├── app/                             # Main application package
│   ├── __init__.py                  # Marks app as a Python package
│   ├── main.py                      # FastAPI app instance, includes routers
│   ├── config.py                    # App configuration (e.g., env vars, settings using Pydantic)
│   ├── database/                    # MongoDB database connection and setup
│   │   ├── __init__.py              # Package init
│   │   └── mongo_db.py              # MongoDB client, database, and collection setup
│   ├── api/                         # API route definitions (pure JSON endpoints)
│   │   ├── __init__.py              # Package init
│   │   ├── api.py                   # Routes for feeds (add/list) and full articles, embed videos, podcast episodes
│   │   ├── articles.py
│   │   ├── youtube.py
│   │   └── podcasts.py
│   ├── core/                        # Core logic that isn't tied to FastAPI or DB directly
│   │   ├── __init__.py              # Package init
│   │   ├── feed_parser.py           # Parses RSS XML feed, extracts feed metadata and items using feedparser/selectolax
│   │   ├── article_parser.py           # Fetches full article content using BeautifulSoup
│   │   ├── youtube_parser.py        # Parses YouTube feeds and embeds videos
│   │   ├── podcast_parser.py        # Parses podcast feed and episodes
│   ├── models/                      # Pydantic models and MongoDB data models
│   │   ├── __init__.py              # Package init
│   │   ├── feed_models.py           # Pydantic models for feeds
│   │   ├── article_models.py        # Pydantic models for news articles
│   │   ├── youtube_models.py        # Pydantic models for YouTube videos
│   │   └── podcast_models.py        # Pydantic models for podcast episodes
│   ├── schemas/  # Pydantic models for requests/responses
│   │   ├── __init__.py
│   │   ├── feed.py
│   │   ├── article.py
│   │   ├── youtube.py
│   │   └── podcast.py
│   ├── crud/                        # CRUD operations for MongoDB
│   │   ├── __init__.py              # Package init
│   │   ├── feed_crud.py             # CRUD operations for feeds
│   │   ├── article_crud.py          # CRUD operations for news articles
│   │   ├── youtube_crud.py          # CRUD operations for YouTube videos
│   │   └── podcast_crud.py          # CRUD operations for podcast episodes
│   ├── services/                    # Services layer containing business logic
│   │   ├── __init__.py              # Package init
│   │   ├── feed_service.py          # Service layer for feeds
│   │   ├── article_service.py       # Service layer for articles
│   │   ├── youtube_service.py       # Service layer for YouTube videos
│   │   └── podcast_service.py       # Service layer for podcast episodes
│   ├── tasks/                   # Replaces Celery tasks
│   │   ├── __init__.py
│   │   ├── scheduler.py            # APScheduler setup
│   │   └── feed_tasks.py           # Scheduled feed updates
└── requirements.txt                 # Dependencies
│   ├── routers/                     # Web routers (optional for testing)
│   │   ├── __init__.py              # Package init
│   │   ├── web.py                   # Template rendering    





