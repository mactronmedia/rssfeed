def normalize_url(url: str) -> str:
    """Normalize URL to prevent duplicates with different formats"""
    url = url.strip()
    if url.endswith('/'):
        url = url[:-1]
    return url.lower()        

url = "https://feeds.bbci.co.uk//"

nul = normalize_url(url)
print(nul)