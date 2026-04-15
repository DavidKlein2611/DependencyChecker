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

    async def check_rubygems(self, package_name: str) -> str:
        url = f"https://rubygems.org/api/v1/gems/{package_name}.json"
        response = await self._make_request(url)
        
        if not response:
            return "Request Error"
            
        if response.status_code == 404:
            return "Not Found (Potentially Vulnerable)"
        elif response.status_code == 200:
            return "Found (Safe)"
        else:
            return f"Error ({response.status_code})"

    async def check_maven(self, package_name: str) -> str:
        # Using Maven Central Solr Search API
        url = f"https://search.maven.org/solrsearch/select?q=a:{package_name}&rows=1&wt=json"
        response = await self._make_request(url)
        
        if not response:
            return "Request Error"
            
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('response', {}).get('numFound', 0) == 0:
                    return "Not Found (Potentially Vulnerable)"
                else:
                    return "Found (Safe)"
            except Exception:
                return "Parse Error"
        else:
            return f"Error ({response.status_code})"

    async def check_package(self, package_info: tuple[str, str]) -> dict:
        package_name, ecosystem = package_info
        scope_status = "N/A"
        npm_status = "N/A"
        pypi_status = "N/A"
        ruby_status = "N/A"
        java_status = "N/A"
        is_critical = False
        is_potentially_vulnerable = False

        if ecosystem == 'npm':
            if package_name.startswith('@'):
                scope = package_name.split('/')[0]
                scope_status = await self.check_npm_scope(scope)
                if 'Critical' in scope_status:
                    is_critical = True

            npm_status = await self.check_npm(package_name)
            is_potentially_vulnerable = 'Potentially Vulnerable' in npm_status
        elif ecosystem == 'python':
            pypi_status = await self.check_pypi(package_name)
            is_potentially_vulnerable = 'Potentially Vulnerable' in pypi_status
        elif ecosystem == 'ruby':
            ruby_status = await self.check_rubygems(package_name)
            is_potentially_vulnerable = 'Potentially Vulnerable' in ruby_status
        elif ecosystem == 'java':
            java_status = await self.check_maven(package_name)
            is_potentially_vulnerable = 'Potentially Vulnerable' in java_status
        
        if is_critical:
            risk = 'Critical'
        elif is_potentially_vulnerable:
            risk = 'High'
        else:
            risk = 'Low'
        
        return {
            'package': package_name,
            'ecosystem': ecosystem,
            'npm_status': npm_status,
            'pypi_status': pypi_status,
            'ruby_status': ruby_status,
            'java_status': java_status,
            'scope_status': scope_status,
            'risk': risk
        }

    async def check_packages(self, packages: set[tuple[str, str]]) -> list[dict]:
        print(f"[*] Verifying {len(packages)} packages with rate limits...")
        tasks = [self.check_package(pkg) for pkg in packages]
        results = await asyncio.gather(*tasks)
        return results
