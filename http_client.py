from curl_cffi import requests
from curl_cffi.requests.errors import RequestsError
import asyncio

class HTTPClient:
    def __init__(self, max_concurrent: int = 10, delay: float = 0.5, proxy: str = None, headers: dict = None, verify: bool = False):
        proxies = {"http": proxy, "https": proxy} if proxy else None
        self.client = requests.AsyncSession(
            timeout=10.0,
            impersonate="chrome110",
            proxies=proxies,
            verify=verify,
            headers=headers
        )
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.delay = delay
        
    async def get(self, url: str, retries: int = 3) -> requests.Response | None:
        """Fetch a URL with rate limiting, returning response or None."""
        for attempt in range(retries):
            async with self.semaphore:
                try:
                    response = await self.client.get(url)
                    if response.status_code == 429 and attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return response
                except (RequestsError, Exception):
                    return None
                finally:
                    if self.delay > 0:
                        await asyncio.sleep(self.delay)
        return None

    async def close(self):
        await self.client.close()
