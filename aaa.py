import requests
import atoma
import time

# URL for the YouTube RSS feed
youtube_rss_url = "https://www.france24.com/es/rss"

# Function to measure atoma speed and print 10 titles
def measure_atoma():
    start_time = time.time()

    response = requests.get(youtube_rss_url)
    feed = atoma.parse_rss_bytes(response.content)

    # Check if the feed is parsed correctly
    if hasattr(feed, 'items'):
        print("Atoma Titles:")
        for entry in feed.items[:10]:
            print(entry.title)
    else:
        print("Failed to parse feed with Atoma")

    elapsed_time = time.time() - start_time
    print(f"\nAtoma: {elapsed_time:.4f} seconds")
    return elapsed_time

if __name__ == "__main__":
    measure_atoma()
