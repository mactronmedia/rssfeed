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



Template: https://chatgpt.com/c/67f69996-6188-800c-8368-5726a4459c36


https://about.fb.com/wp-content/uploads/2016/05/rss-urls-1.pdf



RSS

NAMESPACES:

    'dc': 'http://purl.org/dc/elements/1.1/',
    'atom': 'http://www.w3.org/2005/Atom',
    'atom03': 'http://purl.org/atom/ns#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'rssfake': 'http://purl.org/rss/1.0/',      -- this one can have one thumbnail or more! TAG: <media:content url="
    'media': 'http://search.yahoo.com/mrss/',   -- this one can have one thumbnail or more! TAG: <media:thumbnail url="
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'feed xmlns:yt="http://www.youtube.com/xml/schemas/2015'


RSS Examples:

Youtube:

<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
<link rel="self" href="http://www.youtube.com/feeds/videos.xml?channel_id=UCVls1GmFKf6WlTraIb_IaJg"/>
<id>yt:channel:Vls1GmFKf6WlTraIb_IaJg</id>
<yt:channelId>Vls1GmFKf6WlTraIb_IaJg</yt:channelId>
<title>DistroTube</title>
<link rel="alternate" href="https://www.youtube.com/channel/UCVls1GmFKf6WlTraIb_IaJg"/>
<author>
<name>DistroTube</name>
<uri>https://www.youtube.com/channel/UCVls1GmFKf6WlTraIb_IaJg</uri>
</author>
<published>2017-10-08T15:27:13+00:00</published>
<entry>
<id>yt:video:FA__ScVhGQA</id>
<yt:videoId>FA__ScVhGQA</yt:videoId>
<yt:channelId>UCVls1GmFKf6WlTraIb_IaJg</yt:channelId>
<title>Building Yet Another Pointless Linux Distro</title>
<link rel="alternate" href="https://www.youtube.com/watch?v=FA__ScVhGQA"/>
<author>
<name>DistroTube</name>
<uri>https://www.youtube.com/channel/UCVls1GmFKf6WlTraIb_IaJg</uri>
</author>
<published>2025-04-10T13:00:26+00:00</published>
<updated>2025-04-10T13:00:26+00:00</updated>
<media:group>
<media:title>Building Yet Another Pointless Linux Distro</media:title>
<media:content url="https://www.youtube.com/v/FA__ScVhGQA?version=3" type="application/x-shockwave-flash" width="640" height="390"/>
<media:thumbnail url="https://i3.ytimg.com/vi/FA__ScVhGQA/hqdefault.jpg" width="480" height="360"/>
<media:description>For a few years, I have tinkered with building my own Linux distro (DTOS). It started life as an Arch Linux post-installation script. Then it was an ISO with the calamares installer. Both of these approaches had their pros and cons. Now I'm working on something different for DTOS. WANT TO SUPPORT THE CHANNEL? 💰 Patreon: https://www.patreon.com/distrotube 💳 Paypal: https://www.youtube.com/redirect?event=channel_banner&redir_token=QUFFLUhqazNocEhiaGFBT1l1MnRHbnlIcHFKbXJWVnpQd3xBQ3Jtc0tsLVZJc19YeFlwZ2JqbXVOa3g0Skw4TVhTV2otNm1tM3A1bUNnamh3S2V6OGQtLTBnSjBxYTlvUXMxeEVIS3o4US10NENHMUQ3STk2a01FOFBhUnZjZFctMEhFUTg1TVctQmFfVUdxZXJ4TDl0azlYNA&q=https%3A%2F%2Fwww.paypal.com%2Fcgi-bin%2Fwebscr%3Fcmd%3D_donations%26business%3Dderek%2540distrotube%252ecom%26lc%3DUS%26item_name%3DDistroTube%26no_note%3D0%26currency_code%3DUSD%26bn%3DPP%252dDonationsBF%253abtn_donateCC_LG%252egif%253aNonHostedGuest 🛍️ Amazon: https://amzn.to/2RotFFi 👕 Teespring: https://teespring.com/stores/distrotube DT ON THE WEB: 🕸️ Website: http://distro.tube 📁 GitLab: https://gitlab.com/dwt1 🗨️ Mastodon: https://fosstodon.org/@distrotube 👫 Reddit: https://www.reddit.com/r/DistroTube/ 📽️ Odysee: https://odysee.com/@DistroTube:2 FREE AND OPEN SOURCE SOFTWARE THAT I LIKE: 🌐 Brave Browser - https://brave.com/ 📽️ Open Broadcaster Software: https://obsproject.com/ 🎬 Kdenlive: https://kdenlive.org 🎨 GIMP: https://www.gimp.org/ 💻 VirtualBox: https://www.virtualbox.org/ 🗒️ Doom Emacs: https://github.com/hlissner/doom-emacs Your support is very much appreciated. Thanks, guys!</media:description>
<media:community>
<media:starRating count="625" average="5.00" min="1" max="5"/>
<media:statistics views="9427"/>
</media:community>
</media:group>
</entry>

http://purl.org/rss/1.0/modules/content/
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:wfw="http://wellformedweb.org/CommentAPI/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:sy="http://purl.org/rss/1.0/modules/syndication/" xmlns:slash="http://purl.org/rss/1.0/modules/slash/" xmlns:s="https://www.cbsnews.com/" xmlns:media="http://search.yahoo.com/mrss/" version="2.0">
<channel>
<title>Home - CBSNews.com</title>
<link>https://www.cbsnews.com/</link>
<description>Headlines From CBSNews.com</description>
<pubDate>Fri, 11 Apr 2025 10:04:38 -0400</pubDate>
<ttl>5</ttl>
<item>
<title>Consumers now face "tariff surcharges" for some products at checkout</title>
<link>https://www.cbsnews.com/news/trump-tariff-surcharge-prices/</link>
<description>U.S. businesses are starting to add a tariff fee to customer bills and shopping carts to offset rising import costs.</description>
<pubDate>Fri, 11 Apr 2025 09:37:17 -0400</pubDate>
<image>https://assets2.cbsnewsstatic.com/hub/i/r/2025/04/08/c4eb5149-7d50-481d-a142-eceac569df72/thumbnail/60x60/34b7f365bc4def1017505a9fd042c6a1/gettyimages-2165462299.jpg?v=653dd6912cdd8596c9bfea812c355f95</image>
<guid isPermaLink="false">c7c9ad92-efed-4713-8edb-1f23ae5cb704</guid>
</item>

<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:media="http://search.yahoo.com/mrss/" 
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:media="http://search.yahoo.com/mrss/" >
<channel>
<title>RSSOpinion</title>
<description>RSSOpinion</description>
<link>https://www.wsj.com/opinion</link>
<language>en-us</language>
<copyright>Copyright © Dow Jones & Company, Inc. All rights reserved.</copyright>
<lastBuildDate>Fri, 11 Apr 2025 14:10:36 GMT</lastBuildDate>
<image>
<title>RSSOpinion</title>
<url>http://online.wsj.com/img/wsj_sm_logo.gif</url>
<link>https://www.wsj.com/opinion</link>
</image>
<item>
<guid isPermaLink="false">SB10544384481027173351304592056674015252812</guid>
<title>Does Trump Have a China Trade Strategy?</title>
<description>If he wants Beijing to change, he needs the allies he’s tariffing.</description>
<link>https://www.wsj.com/opinion/china-tariffs-donald-trump-trade-markets-scott-bessent-tiktok-b30bce47</link>
<pubDate>Thu, 10 Apr 2025 21:49:00 GMT</pubDate>
<dc:creator>The Editorial Board</dc:creator>
<media:content url="https://opinion-images.wsj.net/im-39215093" medium="image" type="image/jpeg">
<media:credit>jim watson/Agence France-Presse/Getty Images</media:credit>
</media:content>
</item>