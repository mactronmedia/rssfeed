import aiohttp
from bs4 import BeautifulSoup
from typing import Optional

class ArticleParser:
    @staticmethod
    async def fetch_full_content(url: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Remove unwanted elements
                    for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
                        element.decompose()
                    
                    # Get all paragraphs
                    paragraphs = soup.find_all('p')
                    content = '\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                    
                    return content
        except Exception as e:
            print(f"Error fetching full content: {e}")
            return None