from curl_cffi import requests
from curl_cffi.requests.errors import RequestsError
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio

class Crawler:
    def __init__(self, base_url: str, proxy: str = None, headers: dict = None, max_concurrent: int = 10, delay: float = 0.5, max_depth: int = 1):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_depth = max_depth
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.delay = delay
        
        proxies = {"http": proxy, "https": proxy} if proxy else None
        
        # We use impersonate="chrome110" to spoof the TLS handshake (JA3/JA4 fingerprint) 
        # and automatically inject perfect Chrome HTTP/2 headers.
        self.client = requests.AsyncSession(
            timeout=10.0,
            impersonate="chrome110",
            proxies=proxies,
            verify=False, # Ignore self-signed certs when using interception proxies like Burp
            headers=headers
        )
        
    async def fetch_page(self, url: str, current_depth: int, visited: set, js_urls: set):
        if url in visited or current_depth > self.max_depth:
            return
            
        visited.add(url)
        
        async with self.semaphore:
            try:
                response = await self.client.get(url)
                if response.status_code != 200:
                    return
            except (RequestsError, Exception):
                return
            finally:
                if self.delay > 0:
                    await asyncio.sleep(self.delay)
                    
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find script tags
        for script in soup.find_all('script'):
            src = script.get('src')
            if src:
                full_url = urljoin(url, src)
                js_urls.add(full_url)
                # Guess source map URL
                if full_url.endswith('.js'):
                    js_urls.add(full_url + '.map')
                    
        # Find link tags that might preload JS
        for link in soup.find_all('link', rel='preload', as_='script'):
            href = link.get('href')
            if href:
                full_url = urljoin(url, href)
                js_urls.add(full_url)
                if full_url.endswith('.js'):
                    js_urls.add(full_url + '.map')

        # If we can go deeper, find all a tags
        if current_depth < self.max_depth:
            tasks = []
            for a in soup.find_all('a'):
                href = a.get('href')
                if href:
                    next_url = urljoin(url, href)
                    # Remove fragments/anchors
                    next_url = next_url.split('#')[0]
                    # Ensure it's the same domain to prevent crawling the whole internet
                    if urlparse(next_url).netloc == self.domain and next_url not in visited:
                        tasks.append(self.fetch_page(next_url, current_depth + 1, visited, js_urls))
            
            if tasks:
                await asyncio.gather(*tasks)

    async def discover_js_files(self) -> set[str]:
        """Fetches the homepage and finds JS and JS map files, recursively up to max_depth."""
        print(f"[*] Crawling {self.base_url} for JS files (Max Depth: {self.max_depth})...")
        js_urls = set()
        visited = set()
        
        await self.fetch_page(self.base_url, 1, visited, js_urls)
        
        print(f"[*] Finished crawling. Visited {len(visited)} pages.")
        return js_urls
