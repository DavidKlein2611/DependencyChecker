import httpx
import re
import asyncio

class Extractor:
    def __init__(self, max_concurrent: int = 10, delay: float = 0.5):
        self.client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.delay = delay
        # Common patterns for requires or imports
        # Looks for require('package-name') or import ... from 'package-name'
        self.patterns = [
            re.compile(r"""require\(['"]([^.'"][^'"]+)['"]\)"""),
            re.compile(r"""from\s+['"]([^.'"][^'"]+)['"]"""),
            re.compile(r"""import\s+['"]([^.'"][^'"]+)['"]""")
        ]
        
        # A basic whitelist of common public packages to filter out noise
        self.whitelist = {
            'react', 'react-dom', 'lodash', 'express', 'axios', 'core-js',
            'jquery', 'vue', 'angular', 'moment', 'tslib', 'rxjs', 'next'
        }
        
    def is_likely_internal(self, package_name: str) -> bool:
        """Heuristic to determine if a package name looks internal."""
        if package_name in self.whitelist:
            return False
            
        # Ignore obvious relative paths or built-ins
        if package_name.startswith(('.', '/', '\\')):
            return False
            
        # Ignore standard library-like names (very simplistic check)
        if len(package_name) < 2:
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
                            # Handle scoped packages (e.g. @company/package) and regular packages
                            pkg_name = match.split('/')[0] if not match.startswith('@') else '/'.join(match.split('/')[:2])
                            if self.is_likely_internal(pkg_name):
                                packages.add(pkg_name)
            except httpx.RequestError:
                pass # Silently ignore failed downloads for noisy files like assumed source maps
            finally:
                if self.delay > 0:
                    await asyncio.sleep(self.delay)
            
        return packages

    async def extract_packages(self, urls: set[str]) -> set[str]:
        print(f"[*] Downloading {len(urls)} files with rate limits...")
        all_packages = set()
        
        # Use asyncio.gather to fetch concurrently
        tasks = [self.fetch_and_extract(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        for pkgs in results:
            all_packages.update(pkgs)
            
        await self.client.aclose()
        return all_packages
