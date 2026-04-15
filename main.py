import argparse
from urllib.parse import urlparse
import asyncio
from rich.console import Console

from crawler import Crawler
from extractor import Extractor
from checker import Checker
from reporter import Reporter

console = Console()

# T0 to T5 mapping: (max_concurrent_requests, delay_between_requests_in_seconds)
TIMING_PROFILES = {
    0: (1, 5.0),   # T0: Very slow, very safe
    1: (2, 2.0),   # T1: Slow, still safe
    2: (5, 1.0),   # T2: Slow, a bit faster
    3: (10, 0.5),  # T3: Standard, fine for most servers
    4: (20, 0.1),  # T4: Risky, high chance of being flagged but fast
    5: (50, 0.0)   # T5: Extremely fast, barely any limits
}

async def run(url: str, timing_level: int, proxy: str = None, headers: dict = None, save_json: bool = False, depth: int = 1, insecure: bool = False):
    console.print(f"[bold blue][*][/bold blue] Starting Dependency Confusion Checker for: [bold]{url}[/bold]")
    concurrency, delay = TIMING_PROFILES.get(timing_level, TIMING_PROFILES[3])
    console.print(f"[bold blue][*][/bold blue] Using Timing Profile -T{timing_level} (Concurrency: {concurrency}, Delay: {delay}s)")
    if proxy:
        console.print(f"[bold blue][*][/bold blue] Routing traffic through proxy: {proxy}")
    if headers:
        console.print(f"[bold blue][*][/bold blue] Using {len(headers)} custom headers")
    
    verify_ssl = False if insecure or proxy else True

    # Phase 2: Discovery
    crawler = Crawler(url, proxy=proxy, headers=headers, max_concurrent=concurrency, delay=delay, max_depth=depth, verify=verify_ssl)
    js_urls = await crawler.discover_js_files()
    await crawler.client.close()
    
    if not js_urls:
        console.print("[bold yellow][-][/bold yellow] No JavaScript or source map files found.")
        return
        
    console.print(f"[bold green][+][/bold green] Found {len(js_urls)} potential files to analyze.")
    
    # Phase 3: Extraction
    extractor = Extractor(max_concurrent=concurrency, delay=delay, proxy=proxy, headers=headers, verify=verify_ssl)
    packages = await extractor.extract_packages(js_urls)
    await extractor.client.close()
    
    if not packages:
        console.print("[bold yellow][-][/bold yellow] No potential internal packages found.")
        return
        
    console.print(f"[bold green][+][/bold green] Extracted {len(packages)} unique package names to check.")
    
    # Phase 4: Validation
    checker = Checker(max_concurrent=concurrency, delay=delay, proxy=proxy, verify=verify_ssl)
    findings = await checker.check_packages(packages)
    await checker.client.close()
    
    # Phase 5: Reporting
    reporter = Reporter()
    reporter.generate_report(findings, url, save_json=save_json)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Dependency Confusion Checker")
    parser.add_argument("url", help="The target URL to scan (e.g., https://example.com)")
    parser.add_argument("-T", "--timing", type=int, choices=[0, 1, 2, 3, 4, 5], default=3,
                        help="Timing template (0-5). 0=slowest/safest, 3=default, 5=fastest/riskiest")
    parser.add_argument("-p", "--proxy", type=str, default=None,
                        help="Proxy URL (e.g., http://127.0.0.1:8080) for routing through Burp Suite or a residential proxy")
    parser.add_argument("-H", "--header", action="append", default=[],
                        help="Custom header to include in requests (e.g., 'Authorization: Bearer token'). Can be used multiple times.")
    parser.add_argument("-j", "--json", action="store_true",
                        help="Save the scan results to a JSON file")
    parser.add_argument("-d", "--depth", type=int, default=1,
                        help="Spidering depth (e.g., 1 = homepage only, 2 = homepage + links). Default: 1")
    parser.add_argument("-k", "--insecure", action="store_true",
                        help="Disable SSL certificate verification")
    args = parser.parse_args()
    
    # Parse custom headers
    custom_headers = {}
    for h in args.header:
        if ':' in h:
            key, val = h.split(':', 1)
            custom_headers[key.strip()] = val.strip()
        else:
            console.print(f"[bold yellow][-][/bold yellow] Warning: Invalid header format ignored: {h}")
    
    # Basic URL validation
    parsed_url = urlparse(args.url)
    if not parsed_url.scheme:
        target_url = "https://" + args.url
    else:
        target_url = args.url
        
    asyncio.run(run(target_url, args.timing, args.proxy, custom_headers, args.json, args.depth, args.insecure))
