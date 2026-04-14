import httpx
import asyncio

class Checker:
    def __init__(self, max_concurrent: int = 10, delay: float = 0.5):
        self.client = httpx.AsyncClient(timeout=10.0)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.delay = delay
        self.npm_registry = "https://registry.npmjs.org/"
        self.pypi_registry = "https://pypi.org/pypi/{}/json"
        
    async def _make_request(self, url: str) -> httpx.Response | None:
        """Helper to manage rate-limited requests to registries."""
        async with self.semaphore:
            try:
                response = await self.client.get(url)
                return response
            except httpx.RequestError:
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
            return "Not Found (Vulnerable)"
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
            return "Not Found (Vulnerable)"
        elif response.status_code == 200:
            return "Found (Safe)"
        else:
            return f"Error ({response.status_code})"

    async def check_package(self, package_name: str) -> dict:
        npm_status = await self.check_npm(package_name)
        pypi_status = await self.check_pypi(package_name)
        
        return {
            'package': package_name,
            'npm_status': npm_status,
            'pypi_status': pypi_status,
            'risk': 'High' if 'Vulnerable' in npm_status or 'Vulnerable' in pypi_status else 'Low'
        }

    async def check_packages(self, packages: set[str]) -> list[dict]:
        print(f"[*] Verifying {len(packages)} packages with rate limits...")
        tasks = [self.check_package(pkg) for pkg in packages]
        results = await asyncio.gather(*tasks)
        await self.client.aclose()
        return results
