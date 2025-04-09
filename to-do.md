I'm working on RSS aggregator like Inoreader with FastAPI and MongoDB. The app have two MongoDB collections - feed_urls and feed_news. The app must offer pure API endpoints in json

Features::::

- I can add feed url via web form:- http://rss.cnn.com/rss/money_topstories.rss
- The link is stored in feed_urls collection with title, description, pubDate, image
- Latest news with - items (title, description, link, media:thumbnail url=, description) are stored in feed_news collection
- If I request full article, the article is parsed with BS4 saved to feed_news

Use async and classes!

inoreader_clone/
├── app/                             # Main application package
│   ├── __init__.py                  # Marks app as a Python package
│   ├── main.py                      # FastAPI app instance, includes routers
│   ├── config.py                    # App configuration (e.g., env vars, settings using Pydantic)
│   ├── database/                    # MongoDB database connection and setup
│   │   ├── __init__.py              # Package init
│   │   └── mongo_db.py              # MongoDB client, database and collection setup
│   ├── api/                         # API route definitions (pure JSON endpoints)
│   │   └── rss.py                   # Routes for feeds (add/list) and articles (fetch full content), no template rendering
│   ├── core/                        # Core logic that isn't tied to FastAPI or DB directly
│   │   ├── __init__.py              # Package init
│   │   ├── feed_parser.py           # Parses RSS XML feed, extracts feed metadata and items
│   │   ├── article_parser.py        # Fetches full article content using BeautifulSoup
│   │   └── logger.py                # Centralized logging configuration
│   ├── schemas/                     # Pydantic models for request/response validation
│   │   ├── __init__.py              # Package init
│   │   ├── feed_urls.py             # FeedURLCreate / FeedURLOut models (title, desc, pubDate, etc.)
│   │   └── feed_news.py             # FeedNewsCreate / FeedNewsOut models (news items, full content)
│   ├── services/                    # Business logic between routes and core/crud layers
│   │   ├── feed_service.py          # Handles feed parsing, saving metadata & items to DB
│   │   └── article_service.py       # Handles full article fetching & updating news content
│   ├── crud/                        # Low-level MongoDB operations for each collection
│   │   ├── feed_urls.py             # Insert, get, update feed URLs collection
│   │   └── feed_news.py             # Insert, get, update news items collection
|   ├── routers                      # Web routers
│   ├── templates/                   # Optional HTML templates (e.g., for form submission testing)
│   │   ├── base.html                # Base layout HTML (for shared structure)
│   │   ├── add_feed.html            # Web form to submit a new RSS feed URL
│   │   └── feed_items.html          # Display feed items visually in browser (for dev/debug)
