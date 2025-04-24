from feed_seeker import find_feedly_feeds

for url in find_feedly_feeds('https://www.washingtonpost.com'):
    print(url)