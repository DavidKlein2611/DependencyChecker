import asyncio

class Registry:
    async def check(self, package_name: str) -> dict:
        pass

class NpmRegistry(Registry):
    def __init__(self, http_client):
        self.http_client = http_client
        self.registry_url = "https://registry.npmjs.org/"

    async def check(self, package_name: str) -> dict:
        result = {"npm_status": "N/A", "scope_status": "N/A"}
        
        if package_name.startswith('@'):
            scope = package_name.split('/')[0]
            clean_scope = scope.strip('@')
            url = f"https://registry.npmjs.org/-/org/{clean_scope}/package"
            response = await self.http_client.get(url)
            if not response:
                result["scope_status"] = "Request Error"
            elif response.status_code == 404:
                result["scope_status"] = "Unclaimed Scope (Critical)"
            elif response.status_code == 200:
                result["scope_status"] = "Claimed Scope (Safe)"
            else:
                result["scope_status"] = f"Error ({response.status_code})"

        url = f"{self.registry_url}{package_name}"
        response = await self.http_client.get(url)
        if not response:
            result["npm_status"] = "Request Error"
        elif response.status_code == 404:
            result["npm_status"] = "Not Found (Potentially Vulnerable)"
        elif response.status_code == 200:
            result["npm_status"] = "Found (Safe)"
        else:
            result["npm_status"] = f"Error ({response.status_code})"
            
        return result

class PypiRegistry(Registry):
    def __init__(self, http_client):
        self.http_client = http_client
        self.registry_url = "https://pypi.org/pypi/{}/json"

    async def check(self, package_name: str) -> dict:
        result = {"pypi_status": "N/A"}
        if package_name.startswith('@'):
            result["pypi_status"] = "N/A (Scoped)"
            return result
            
        url = self.registry_url.format(package_name)
        response = await self.http_client.get(url)
        if not response:
            result["pypi_status"] = "Request Error"
        elif response.status_code == 404:
            result["pypi_status"] = "Not Found (Potentially Vulnerable)"
        elif response.status_code == 200:
            result["pypi_status"] = "Found (Safe)"
        else:
            result["pypi_status"] = f"Error ({response.status_code})"
        return result

class RubyGemsRegistry(Registry):
    def __init__(self, http_client):
        self.http_client = http_client

    async def check(self, package_name: str) -> dict:
        result = {"ruby_status": "N/A"}
        url = f"https://rubygems.org/api/v1/gems/{package_name}.json"
        response = await self.http_client.get(url)
        if not response:
            result["ruby_status"] = "Request Error"
        elif response.status_code == 404:
            result["ruby_status"] = "Not Found (Potentially Vulnerable)"
        elif response.status_code == 200:
            result["ruby_status"] = "Found (Safe)"
        else:
            result["ruby_status"] = f"Error ({response.status_code})"
        return result

class MavenRegistry(Registry):
    def __init__(self, http_client):
        self.http_client = http_client

    async def check(self, package_name: str) -> dict:
        result = {"java_status": "N/A"}
        url = f"https://search.maven.org/solrsearch/select?q=a:{package_name}&rows=1&wt=json"
        response = await self.http_client.get(url)
        if not response:
            result["java_status"] = "Request Error"
        elif response.status_code == 200:
            try:
                data = response.json()
                if data.get("response", {}).get("numFound", 0) == 0:
                    result["java_status"] = "Not Found (Potentially Vulnerable)"
                else:
                    result["java_status"] = "Found (Safe)"
            except Exception:
                result["java_status"] = "Parse Error"
        else:
            result["java_status"] = f"Error ({response.status_code})"
        return result

class Checker:
    def __init__(self, adapters=None):
        self.adapters = adapters or {}

    async def check_package(self, package_info: tuple[str, str]) -> dict:
        package_name, ecosystem = package_info
        
        base_result = {
            "package": package_name,
            "ecosystem": ecosystem,
            "npm_status": "N/A",
            "pypi_status": "N/A",
            "ruby_status": "N/A",
            "java_status": "N/A",
            "scope_status": "N/A",
            "risk": "Low"
        }

        adapter = self.adapters.get(ecosystem)
        if adapter:
            status_dict = await adapter.check(package_name)
            base_result.update(status_dict)

        is_critical = "Critical" in base_result.get("scope_status", "")
        is_potentially_vulnerable = any(
            "Potentially Vulnerable" in str(val) 
            for key, val in base_result.items() 
            if key.endswith("_status")
        )

        if is_critical:
            base_result["risk"] = "Critical"
        elif is_potentially_vulnerable:
            if base_result.get("scope_status") == "Claimed Scope (Safe)":
                pass
            else:
                base_result["risk"] = "High"
            
        return base_result

    async def check_packages(self, packages: set[tuple[str, str]]) -> list[dict]:
        print(f"[*] Verifying {len(packages)} packages...")
        tasks = [self.check_package(pkg) for pkg in packages]
        results = await asyncio.gather(*tasks)
        return results