from curl_cffi import requests
from curl_cffi.requests.errors import RequestsError
import re
import asyncio

class Extractor:
    def __init__(self, max_concurrent: int = 10, delay: float = 0.5, proxy: str = None, headers: dict = None):
        proxies = {"http": proxy, "https": proxy} if proxy else None
        self.client = requests.AsyncSession(
            timeout=10.0,
            impersonate="chrome110",
            proxies=proxies,
            verify=False,
            headers=headers
        )
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.delay = delay
        # Common patterns for requires or imports
        self.patterns = [
            re.compile(r"""require\(['"]([^.'"][^'"]+)['"]\)"""),
            re.compile(r"""from\s+['"]([^.'"][^'"]+)['"]"""),
            re.compile(r"""import\s+['"]([^.'"][^'"]+)['"]""")
        ]
        
        self.whitelist = {
            'react', 'react-dom', 'lodash', 'express', 'axios', 'core-js',
            'jquery', 'vue', 'angular', 'moment', 'tslib', 'rxjs', 'next'
        }
        
    def is_likely_internal(self, package_name: str) -> bool:
        if package_name in self.whitelist:
            return False
        if package_name.startswith(('.', '/', '\\')):
            return False
        if len(package_name) < 2:
            return False
        # Filter out dynamic variables, template strings (e.g. ${s}), or malformed names
        if not re.match(r"^@?[a-z0-9][a-z0-9._-]*$", package_name, re.IGNORECASE):
            return False
        return True

    async def fetch_and_extract(self, url: str) -> set[str]:
        packages = set()
        async with self.semaphore:
            try:
                response = await self.client.get(url)
                if response.status_code == 200:
                    content = response.text
                    for pattern in self.patterns:
                        matches = pattern.findall(content)
                        for match in matches:
                            pkg_name = match.split('/')[0] if not match.startswith('@') else '/'.join(match.split('/')[:2])
                            if self.is_likely_internal(pkg_name):
                                packages.add(pkg_name)
            except (RequestsError, Exception):
                pass # Silently ignore failed downloads for noisy files like assumed source maps
            finally:
                if self.delay > 0:
                    await asyncio.sleep(self.delay)
            
        return packages

    async def extract_packages(self, urls: set[str]) -> set[str]:
        print(f"[*] Downloading {len(urls)} files with rate limits...")
        all_packages = set()
        
        tasks = [self.fetch_and_extract(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        for pkgs in results:
            all_packages.update(pkgs)
            
        return all_packages
