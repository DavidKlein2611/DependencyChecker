import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio

class Crawler:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        self.domain = urlparse(base_url).netloc
        
    async def discover_js_files(self) -> set[str]:
        """Fetches the homepage and finds JS and JS map files."""
        print(f"[*] Crawling {self.base_url} for JS files...")
        js_urls = set()
        
        try:
            response = await self.client.get(self.base_url)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"[-] Failed to fetch {self.base_url}: {e}")
            return js_urls
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find script tags
        for script in soup.find_all('script'):
            src = script.get('src')
            if src:
                full_url = urljoin(self.base_url, src)
                js_urls.add(full_url)
                # Guess source map URL
                if full_url.endswith('.js'):
                    js_urls.add(full_url + '.map')
                    
        # Find link tags that might preload JS
        for link in soup.find_all('link', rel='preload', as_='script'):
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                js_urls.add(full_url)
                if full_url.endswith('.js'):
                    js_urls.add(full_url + '.map')
                    
        await self.client.aclose()
        return js_urls
