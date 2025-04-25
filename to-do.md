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








    rss_urls = [
        
        'https://feeds.feedburner.com/MachineLearningMastery',
        'https://kingy.ai/feed/',
        'https://rss.slashdot.org/Slashdot/slashdotLinux',
        'https://feeds.feedburner.com/d0od',
        'https://feeds.feedburner.com/Phoronix',
        'https://www.ubuntu.com/rss.xml',
        'http://lxer.com/module/newswire/headlines.rss',
        'https://www.howtoforge.com/node/feed',
        'https://feeds.feedburner.com/ItsFoss',
        'https://www.tecmint.com/feed/',
        'https://www.cnet.com/rss/news/',
        'https://www.digitaltrends.com/feed/',
        'https://www.makeuseof.com/feed/',
        'https://lifehacker.com/feed',
        'https://www.engadget.com/rss.xml',
        'https://feeds.arstechnica.com/arstechnica/index',
        'https://therecord.media/feed',
        'https://www.securityweek.com/feed/',
        'https://krebsonsecurity.com/feed/',
        'https://thehackernews.com/feeds/posts/default',
        'https://www.wpbeginner.com/feed/',
        'http://feeds.searchenginejournal.com/SearchEngineJournal',
        'http://feeds.seroundtable.com/SearchEngineRoundtable1',
        'https://contentmarketinginstitute.com/blog/feed/',
        'https://moz.com/feeds/blog.rss',
        'https://www.youtube.com/feeds/videos.xml?channel_id=UCj7v9UM1aGx6GR-nsY-9u8w',
        'https://feeds.searchengineland.com/searchengineland',
        'https://ahrefs.com/blog/feed/',
        'https://sproutsocial.com/insights/feed/',
        'https://www.convinceandconvert.com/blog/feed/',
        'https://www.getresponse.com/blog/feed',
        'https://www.searchenginewatch.com/feed/',
        'https://learn.g2.com/rss.xml',
        'https://www.demandsage.com/feed/',
        'https://www.socialmediaexaminer.com/feed/',
        'https://www.intentsify.io/blog/rss.xml',
        'https://copyblogger.com/feed/',
        'https://diymarketers.com/feed/',
        'https://elitedigitalagency.com/blog/feed/',
        'https://www.smartinsights.com/blog/feed/',
        'https://www.semrush.com/blog/feed/',
        'https://verticalresponse.com/feed/',
        'https://www.reachfirst.com/feed/',
        'https://neilpatel.com/blog/feed/',
        'https://www.developernation.net/rss.xml',
        'https://www.pcmag.com/feeds/rss/latest',
        'https://www.tomsguide.com/feeds.xml',
        'https://www.gamingonlinux.com/article_rss.php',
        'https://www.maketecheasier.com/feed/',
        'https://www.networkworld.com/feed/',
        'https://linuxconfig.org/feed',
        'https://www.rosehosting.com/blog/feed/',
        'https://bashscript.net/feed/',
        'https://linuxgizmos.com/feed/',
        'https://9to5linux.com/feed',
        'https://fedoramagazine.org/feed/',
        'https://fossforce.com/feed',
        'https://www.phoronix.com/rss.php',
        'https://linuxiac.com/feed/',
        'https://www.linuxjournal.com/node/feed',
        'https://www.index.hr/rss/magazin',
        'https://www.index.hr/rss/sport',
        'https://www.index.hr/rss/vijesti-novac',
        'https://www.index.hr/rss/vijesti-hrvatska',
        'https://www.index.hr/rss/vijesti-znanost',
        'https://www.index.hr/rss/vijesti-svijet',
        'https://www.index.hr/rss/vijesti',
        'https://www.index.hr/rss/najcitanije',
        'https://www.index.hr/rss',
        'https://www.websiteplanet.com/feed/',
        'https://dnevnik.hr/assets/feed/articles',
        'https://www.bloomberg.com/politics/feeds/site.xml',
        'https://www.techradar.com/rss',
        'https://www.zdnet.com/news/rss.xml',
        'https://techcrunch.com/feed/',
        'https://www.technewsworld.com/rss-feed',
        'https://dig.watch/feed',
        'https://globalnews.ca/feed/',
        'https://www.saltwire.com/feed',
        'https://www.cbc.ca/webfeed/rss/rss-Indigenous',
        'https://www.cbc.ca/webfeed/rss/rss-technology',
        'https://www.cbc.ca/webfeed/rss/rss-arts',
        'https://www.cbc.ca/webfeed/rss/rss-health',
        'https://www.cbc.ca/webfeed/rss/rss-business',
        'https://www.cbc.ca/webfeed/rss/rss-politics',
        'https://www.cbc.ca/webfeed/rss/rss-canada',
        'https://www.cbc.ca/webfeed/rss/rss-world',
        'https://www.cbc.ca/webfeed/rss/rss-topstories',
        'https://feeds.npr.org/1003/rss.xml',
        'https://feeds.npr.org/1004/rss.xml',
        'https://feeds.feedburner.com/TheAtlanticWire',
        'https://time.com/newsfeed/feed/',
        'https://feeds.feedburner.com/dailykos/zyrjlhwgaef',
        'https://www.thenation.com/feed/?post_type=article',
        'https://www.ft.com/rss/home',
        'https://www.smithsonianmag.com/rss/science-nature/',
        'https://feeds.feedburner.com/foodsafetynews/mRcs',
        'https://www.howtogeek.com/feed/',
        'https://news.yahoo.com/rss/us',
        'https://www.tmz.com/rss.xml',
        'https://www.cnet.com/rss/news/',
        'https://www.cnet.com/rss/how-to/',
        'https://www.cnet.com/rss/deals/',
        'https://www.newsweek.com/rss',
        'https://moxie.foxnews.com/google-publisher/latest.xml',
        'https://feeds.nbcnews.com/msnbc/public/news',
        'https://time.com/feed/',
        'https://www.vice.com/en/feed/',
        'https://feeds.washingtonpost.com/rss/entertainment',
        'https://feeds.washingtonpost.com/rss/world',
        'https://www.arabnews.com/rss.xml',
        'https://medium.com/feed/tomtalkspython',
        'https://www.gsmarena.com/rss-news-reviews.php3',
        'https://www.intelligentcio.com/feed/',
        'https://www.gamespress.com/News/RSS',
        'https://qz.com/rss',
        'https://www.independent.co.uk/rss',
        'https://feeds.bbci.co.uk/news/rss.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Africa.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Americas.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/AsiaPacific.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Europe.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/MiddleEast.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/US.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Education.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/EnergyEnvironment.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/SmallBusiness.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Dealbook.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/MediaandAdvertising.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/YourMoney.xml',
        'https://www.aljazeera.com/xml/rss/all.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/PersonalTech.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Baseball.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Science.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Climate.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Space.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Health.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Well.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/ArtandDesign.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Books/Review.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Dance.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Movies.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Music.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Television.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Theater.xml',
        'https://feeds.skynews.com/feeds/rss/home.xml',
        'https://abcnews.go.com/abcnews/usheadlines',
        'https://www.cbsnews.com/latest/rss/main',
        'https://feeds.content.dowjones.io/public/rss/RSSOpinion',
        'https://feeds.nbcnews.com/nbcnews/public/world',
        'https://www.newyorker.com/feed/news',
        'https://www.theguardian.com/us-news/rss',
        'https://www.latimes.com/world/rss2.0.xml',
        'https://www.yorkshireeveningpost.co.uk/rss',
        'https://orthodoxtimes.com/feed/',
        'https://mashable.com/feeds/rss/all',
        'https://indianexpress.com/feed/',
        'https://www.theverge.com/rss/index.xml',
        'https://arstechnica.com/feed/',
        'https://www.engadget.com/rss.xml',
        'https://www.wired.com/feed',
        'https://www.deutschland.de/en/feed',
        'https://www.spiegel.de/index.rss',
        'https://img.rtvslo.si/feeds/00.xml',
        'https://www.france24.com/fr/rss',
        'https://www.france24.com/es/rss'
        
    ]
