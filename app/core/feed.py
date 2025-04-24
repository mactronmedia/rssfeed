# Import the necessary module from trafilatura
from trafilatura import feeds

# Find feed URLs from the website
mylist = feeds.find_feed_urls('https://www.omgubuntu.co.uk/')

# Output the number of feed URLs found (the length can change over time)
print(len(mylist))  # 74 (or a different number depending on the time)

# Print out the feed URLs found
print(mylist)

# Use a specific feed URL directly
mylist = feeds.find_feed_urls('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml')

# Check if the list is not empty
print(mylist != [])  # This will print 'True' if it's not empty, indicating success
