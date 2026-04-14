import argparse
from urllib.parse import urlparse
import asyncio

from crawler import Crawler
from extractor import Extractor
from checker import Checker
from reporter import Reporter

# T0 to T5 mapping: (max_concurrent_requests, delay_between_requests_in_seconds)
TIMING_PROFILES = {
    0: (1, 5.0),   # T0: Very slow, very safe
    1: (2, 2.0),   # T1: Slow, still safe
    2: (5, 1.0),   # T2: Slow, a bit faster
    3: (10, 0.5),  # T3: Standard, fine for most servers
    4: (20, 0.1),  # T4: Risky, high chance of being flagged but fast
    5: (50, 0.0)   # T5: Extremely fast, barely any limits
}

async def run(url: str, timing_level: int):
    print(f"[*] Starting Dependency Confusion Checker for: {url}")
    concurrency, delay = TIMING_PROFILES.get(timing_level, TIMING_PROFILES[3])
    print(f"[*] Using Timing Profile -T{timing_level} (Concurrency: {concurrency}, Delay: {delay}s)")
    
    # Phase 2: Discovery
    crawler = Crawler(url)
    js_urls = await crawler.discover_js_files()
    
    if not js_urls:
        print("[-] No JavaScript or source map files found.")
        return
        
    print(f"[+] Found {len(js_urls)} potential files to analyze.")
    
    # Phase 3: Extraction
    extractor = Extractor(max_concurrent=concurrency, delay=delay)
    packages = await extractor.extract_packages(js_urls)
    
    if not packages:
        print("[-] No potential internal packages found.")
        return
        
    print(f"[+] Extracted {len(packages)} unique package names to check.")
    
    # Phase 4: Validation
    checker = Checker(max_concurrent=concurrency, delay=delay)
    findings = await checker.check_packages(packages)
    
    # Phase 5: Reporting
    reporter = Reporter()
    reporter.generate_report(findings, url)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Dependency Confusion Checker")
    parser.add_argument("url", help="The target URL to scan (e.g., https://example.com)")
    parser.add_argument("-T", "--timing", type=int, choices=[0, 1, 2, 3, 4, 5], default=3,
                        help="Timing template (0-5). 0=slowest/safest, 3=default, 5=fastest/riskiest")
    args = parser.parse_args()
    
    # Basic URL validation
    parsed_url = urlparse(args.url)
    if not parsed_url.scheme:
        target_url = "https://" + args.url
    else:
        target_url = args.url
        
    asyncio.run(run(target_url, args.timing))
