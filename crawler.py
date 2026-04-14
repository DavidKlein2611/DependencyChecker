from curl_cffi import requests
from curl_cffi.requests.errors import RequestsError
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio

class Crawler:
    def __init__(self, base_url: str, proxy: str = None, headers: dict = None):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        
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
        
    async def discover_js_files(self) -> set[str]:
        """Fetches the homepage and finds JS and JS map files."""
        print(f"[*] Crawling {self.base_url} for JS files...")
        js_urls = set()
        
        try:
            response = await self.client.get(self.base_url)
            response.raise_for_status()
        except RequestsError as e:
            print(f"[-] Network/TLS Error fetching {self.base_url}: {e}")
            return js_urls
        except Exception as e:
            print(f"[-] HTTP Error fetching {self.base_url}: {e}")
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
                    
        # The session should be closed ideally, but python gc handles simple scripts fine.
        return js_urls
