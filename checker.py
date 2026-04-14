from curl_cffi import requests
from curl_cffi.requests.errors import RequestsError
import asyncio

class Checker:
    def __init__(self, max_concurrent: int = 10, delay: float = 0.5, proxy: str = None):
        proxies = {"http": proxy, "https": proxy} if proxy else None
        self.client = requests.AsyncSession(
            timeout=10.0,
            impersonate="chrome110",
            proxies=proxies,
            verify=False
        )
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.delay = delay
        self.npm_registry = "https://registry.npmjs.org/"
        self.pypi_registry = "https://pypi.org/pypi/{}/json"
        
    async def _make_request(self, url: str) -> requests.Response | None:
        """Helper to manage rate-limited requests to registries."""
        async with self.semaphore:
            try:
                response = await self.client.get(url)
                return response
            except (RequestsError, Exception):
                return None
            finally:
                if self.delay > 0:
                    await asyncio.sleep(self.delay)

    async def check_npm(self, package_name: str) -> str:
        url = f"{self.npm_registry}{package_name}"
        response = await self._make_request(url)
        
        if not response:
            return "Request Error"
            
        if response.status_code == 404:
            return "Not Found (Potentially Vulnerable)"
        elif response.status_code == 200:
            return "Found (Safe)"
        else:
            return f"Error ({response.status_code})"

    async def check_pypi(self, package_name: str) -> str:
        # PyPI doesn't use scoped names like @scope/pkg, so we skip if it's scoped
        if package_name.startswith('@'):
            return "N/A (Scoped)"
            
        url = self.pypi_registry.format(package_name)
        response = await self._make_request(url)
        
        if not response:
            return "Request Error"
            
        if response.status_code == 404:
            return "Not Found (Potentially Vulnerable)"
        elif response.status_code == 200:
            return "Found (Safe)"
        else:
            return f"Error ({response.status_code})"

    async def check_npm_scope(self, scope_name: str) -> str:
        # Check if the org/scope exists
        clean_scope = scope_name.strip('@')
        url = f"https://registry.npmjs.org/-/org/{clean_scope}/package"
        response = await self._make_request(url)
        
        if not response:
            return "Request Error"
            
        if response.status_code == 404:
            return "Unclaimed Scope (Critical)"
        elif response.status_code == 200:
            return "Claimed Scope (Safe)"
        else:
            return f"Error ({response.status_code})"

    async def check_package(self, package_name: str) -> dict:
        scope_status = "N/A"
        is_critical = False
        
        if package_name.startswith('@'):
            scope = package_name.split('/')[0]
            scope_status = await self.check_npm_scope(scope)
            if 'Critical' in scope_status:
                is_critical = True

        npm_status = await self.check_npm(package_name)
        pypi_status = await self.check_pypi(package_name)
        
        # Since we only extract from .js files right now, these are JavaScript packages.
        # They are only potentially vulnerable if they are missing from NPM.
        is_potentially_vulnerable = 'Potentially Vulnerable' in npm_status
        
        if is_critical:
            risk = 'Critical'
        elif is_potentially_vulnerable:
            risk = 'High'
        else:
            risk = 'Low'
        
        return {
            'package': package_name,
            'npm_status': npm_status,
            'pypi_status': pypi_status,
            'scope_status': scope_status,
            'risk': risk
        }

    async def check_packages(self, packages: set[str]) -> list[dict]:
        print(f"[*] Verifying {len(packages)} packages with rate limits...")
        tasks = [self.check_package(pkg) for pkg in packages]
        results = await asyncio.gather(*tasks)
        return results
