import asyncio
from mitmproxy import http
from mitmproxy import ctx
from extractor import Extractor
from checker import Checker
from rich.console import Console

console = Console()

class DependencyConfusionAddon:
    def __init__(self):
        # Initialize the Extractor and Checker
        # We don't need proxies for passive mode as the traffic is already flowing through mitmproxy
        self.extractor = Extractor()
        self.checker = Checker()
        
        # Keep track of what we've seen to avoid redundant processing
        self.analyzed_urls = set()
        self.checked_packages = set()

        console.print("[bold green][+][/bold green] Passive Dependency Confusion Scanner Loaded!")
        console.print("[i]Browse the target site through this proxy. Background scanning is active...[/i]\n")

    async def response(self, flow: http.HTTPFlow):
        # Only process responses with a successful HTTP status code
        if not flow.response or flow.response.status_code != 200:
            return

        url = flow.request.pretty_url
        
        # Filter for relevant file extensions and common manifest names
        is_js = ".js" in url or ".map" in url
        manifests = ['requirements.txt', 'Pipfile', 'Gemfile', 'Gemfile.lock', 'pom.xml', 'build.gradle']
        is_manifest = any(url.endswith(m) for m in manifests)
        
        if (is_js or is_manifest) and url not in self.analyzed_urls:
            self.analyzed_urls.add(url)
            
            # Extract raw text from the HTTP response
            content = flow.response.get_text(strict=False)
            if not content:
                return

            # Extract packages directly from the text
            packages = self.extractor.extract_from_text(content, url)
            
            # Filter out packages we have already checked during this session
            new_packages = {pkg for pkg in packages if pkg[0] not in self.checked_packages}
            
            if new_packages:
                for pkg_name, _ in new_packages:
                    self.checked_packages.add(pkg_name)
                
                # Run the verification in the background to avoid blocking the proxy
                asyncio.create_task(self.verify_and_alert(new_packages, url))

    async def verify_and_alert(self, packages: set[tuple[str, str]], source_url: str):
        findings = await self.checker.check_packages(packages)
        
        for finding in findings:
            risk = finding['risk']
            if risk in ['High', 'Critical']:
                if risk == 'Critical':
                    console.print(f"\n[bold red blink][!!!] CRITICAL VULNERABILITY DETECTED [!!!][/bold red blink]")
                else:
                    console.print(f"\n[bold yellow][!] HIGH RISK VULNERABILITY DETECTED [!][/bold yellow]")
                
                console.print(f"[bold]Source URL:[/bold] {source_url}")
                console.print(f"[bold]Package:[/bold] {finding['package']} ({finding['ecosystem']})")
                
                if finding['ecosystem'] == 'npm':
                    console.print(f"    [bold]NPM Status:[/bold] {finding['npm_status']}")
                    if finding['scope_status'] != 'N/A':
                        console.print(f"    [bold]Scope Status:[/bold] {finding['scope_status']}")
                elif finding['ecosystem'] == 'python':
                    console.print(f"    [bold]PyPI Status:[/bold] {finding['pypi_status']}")
                elif finding['ecosystem'] == 'ruby':
                    console.print(f"    [bold]RubyGems Status:[/bold] {finding['ruby_status']}")
                elif finding['ecosystem'] == 'java':
                    console.print(f"    [bold]Maven Status:[/bold] {finding['java_status']}")
                
                console.print("-" * 50)

    def done(self):
        # Cleanup tasks if mitmproxy is shutting down
        asyncio.create_task(self.extractor.client.close())
        asyncio.create_task(self.checker.client.close())

# mitmproxy looks for the 'addons' list
addons = [
    DependencyConfusionAddon()
]