import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from datetime import datetime
import requests
from lxml import html as lxml_html
import re

class ArticleScraper:
    @staticmethod
    def parse_article(html: str, url: str) -> Dict[str, Any]:
        """Parse article content from HTML with improved content extraction."""
        try:
            tree = lxml_html.fromstring(html)
            
            def extract_first(xpaths: List[str], join_text: bool = True) -> Optional[str]:
                for xpath in xpaths:
                    results = tree.xpath(xpath)
                    if results:
                        text = results[0].strip()
                        if join_text:
                            text = ' '.join(text.split())
                        return text
                return None
            
            def extract_all_elements(xpaths: List[str]) -> str:
                for xpath in xpaths:
                    elements = tree.xpath(xpath)
                    if elements:
                        cleaned_elements = []
                        for el in elements:
                            # Remove unwanted elements first
                            for bad in el.xpath('.//script|.//style|.//iframe|.//noscript|.//object|.//embed'):
                                bad.getparent().remove(bad)
                            
                            # Keep only allowed HTML tags and remove attributes
                            html_content = lxml_html.tostring(el, encoding='unicode')
                            
                            # First remove all unwanted tags completely
                            html_content = re.sub(r'<(/?)(script|style|iframe|noscript|object|embed|form|input|button|select|textarea)([^>]*)?>', '', html_content)
                            
                            # Then clean allowed tags (remove attributes)
                            html_content = re.sub(r'<(/?)(p|a|img|br|div|span|strong|em|ul|ol|li|h[1-6])(\s[^>]*)?>', r'<\1\2>', html_content)
                            
                            # Clean up whitespace
                            html_content = re.sub(r'\s+', ' ', html_content).strip()
                            
                            if html_content:
                                cleaned_elements.append(html_content)
                        if cleaned_elements:
                            return '\n'.join(cleaned_elements)
                return ''
            
            title = extract_first([
                '//h1[not(contains(@class, "header"))]//text()',
                '//meta[@property="og:title"]/@content',
                '//meta[@name="twitter:title"]/@content',
                '//title/text()'
            ])
            
            pub_date = extract_first([
                '//meta[@property="article:published_time"]/@content',
                '//meta[@name="date"]/@content',
                '//time[contains(@class, "date")]/@datetime',
                '//time/@datetime',
                '//span[contains(@class, "date")]/text()'
            ])
            
            author = extract_first([
                '//meta[@name="author"]/@content',
                '//meta[@property="article:author"]/@content',
                '//a[contains(@class, "author")]//text()',
                '//span[contains(@class, "author")]//text()'
            ])
            
            content = extract_all_elements([
                '//article//div[contains(@class, "article-body")]',
                '//article//div[contains(@class, "post-content")]',
                '//article//div[@itemprop="articleBody"]',
                '//article',
                '//div[contains(@class, "content")]',
                '//div[contains(@class, "main-content")]'
            ])
            
            if len(content) > 10000:
                content = extract_all_elements([
                    '//article//p[not(ancestor::footer)]',
                    '//div[contains(@class, "article-body")]//p',
                    '//div[@itemprop="articleBody"]//p'
                ])
            
            if content:
                content = re.sub(r'\n{3,}', '\n\n', content)
                content = content.strip()
            
            image = None
            for xpath in [
                '//meta[@property="og:image"]/@content',
                '//meta[@name="twitter:image"]/@content',
                '//figure[contains(@class, "main")]//img/@src',
                '//div[contains(@class, "hero-image")]//img/@src',
                '//article//img[1]/@src'
            ]:
                results = tree.xpath(xpath)
                if results:
                    image = urljoin(url, results[0])
                    break
            
            return {
                'title': title,
                'url': url,
                'published_date': pub_date,
                'author': author,
                'content': content if content else None,
                'image_url': image,
                'scraped_at': datetime.utcnow().isoformat(),
                'content_length': len(content) if content else 0
            }
            
        except Exception as e:
            logging.error(f"Error parsing article {url}: {str(e)}", exc_info=True)
            return {
                'url': url,
                'scraped_at': datetime.utcnow().isoformat(),
                'error': str(e)
            }

def fetch_html(url: str) -> Optional[str]:
    """Fetch HTML content from a URL with improved headers and timeout."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = requests.get(url, headers=headers, timeout=(3.05, 27))
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.error(f"Error fetching URL {url}: {str(e)}")
        return None

def main():
    """Demonstrate the improved article scraper."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    test_urls = [
        'https://www.washingtonpost.com/entertainment/2025/04/18/kennedy-center-layoffs/'
    ]
    
    for url in test_urls:
        logging.info(f"\nProcessing: {url}")
        
        html = fetch_html(url)
        if not html:
            logging.warning("Failed to fetch HTML")
            continue
        
        article = ArticleScraper.parse_article(html, url)
        
        print(f"\nTitle: {article.get('title')}")
        print(f"Date: {article.get('published_date')}")
        print(f"Author: {article.get('author')}")
        print(f"Content Length: {article.get('content_length', 0)} characters")
        print(f"Image: {article.get('image_url')}")
        
        if 'error' in article:
            print(f"Error: {article['error']}")
        
        content = article.get('content', '')
        print("\nContent Preview:")
        print(content)

if __name__ == "__main__":
    main()