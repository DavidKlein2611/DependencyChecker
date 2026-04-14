# Automated Dependency Confusion Checker

## Overview
The Automated Dependency Confusion Checker is a specialized security testing tool designed to identify potential dependency confusion (supply chain) vulnerabilities in web applications. The tool automates the discovery phase by crawling a target domain for JavaScript and dependency manifest files (Python, Ruby, Java), extracting imported package names via AST-like regular expression matching and file parsing, and verifying their existence against public package registries (NPM, PyPI, RubyGems, Maven Central).

If an internal-looking package name is referenced in the target's source code or configuration files but does not exist on the public registry, the tool flags it as a high-risk candidate for a dependency confusion attack.

## Core Features
* **Multi-Ecosystem Support:** Discovers and parses dependency manifests across multiple languages including Python (`requirements.txt`, `Pipfile`), Ruby (`Gemfile`, `Gemfile.lock`), and Java (`pom.xml`, `build.gradle`), checking packages against PyPI, RubyGems, and Maven Central.
* **Modern JS Framework Heuristics:** Employs advanced regex patterns to extract internal dependencies from compiled Webpack chunk definitions and Vite module registries, ensuring coverage for modern Single Page Applications.
* **Asynchronous Execution:** Utilizes Python's `asyncio` for highly concurrent network requests, file downloading, and API validation.
* **Advanced WAF Evasion:** Implements `curl_cffi` to spoof modern browser TLS fingerprints (JA3/JA4) and HTTP/2 headers. This effectively bypasses strict Web Application Firewalls (WAFs) like Cloudflare and AWS WAF that block generic Python scripts.
* **Timing Profiles:** NMAP-style timing templates (`-T0` to `-T5`) provide granular control over connection concurrency and request delays, preventing accidental Denial of Service (DoS) and mitigating rate-limiting on target infrastructure.
* **Interception Proxy Support:** Native support for upstream proxies, allowing operators to route traffic through Burp Suite, Caido, or residential proxy networks for deep traffic analysis and IP masking.
* **Automated Reporting:** Consolidates findings into a clean terminal summary and generates a structured JSON report for documentation and subsequent validation.

## Prerequisites
* Python 3.10+

## Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/DavidKlein2611/DepenedencyChecker
   cd DependencyChecker
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

```text
usage: main.py [-h] [-T {0,1,2,3,4,5}] [-p PROXY] [-H HEADER] [-j] [-d DEPTH] url

Automated Dependency Confusion Checker

positional arguments:
  url                   The target URL to scan (e.g., https://example.com)

options:
  -h, --help            show this help message and exit
  -T {0,1,2,3,4,5}, --timing {0,1,2,3,4,5}
                        Timing template (0-5). 0=slowest/safest, 3=default, 5=fastest/riskiest
  -p PROXY, --proxy PROXY
                        Proxy URL (e.g., http://127.0.0.1:8080) for routing through Burp Suite or a residential proxy
  -H HEADER, --header HEADER
                        Custom header to include in requests (e.g., 'Authorization: Bearer token'). Can be used multiple times.
  -j, --json            Save the scan results to a JSON file
  -d DEPTH, --depth DEPTH
                        Spidering depth (e.g., 1 = homepage only, 2 = homepage + links). Default: 1
```

### Examples

**Standard Scan:**
Executes with default settings.
```bash
python main.py https://target.com
```

**Deep Spidering Scan:**
Recursively crawls all internal links up to a depth of 3 to discover hidden JavaScript chunks in large Single Page Applications.
```bash
python main.py -d 3 https://target.com
```

**Scan and Save to JSON:**
Outputs findings to the terminal and saves a detailed JSON report.
```bash
python main.py -j https://target.com
```

**Stealth Scan:**
Executes with a slow timing profile (`-T 1`) to evade behavioral WAF detections and abide by rate limit RoEs.
```bash
python main.py -T 1 https://target.com
```

**Authenticated Scan (Custom Headers):**
Passes specific headers to the target to bypass authentication layers or meet VDP requirements.
```bash
python main.py -T 2 -H "Authorization: Bearer <token>" -H "Cookie: session=123" https://target.com
```

**Proxied Scan:**
Routes all traffic through a local interception proxy (like Burp Suite).
```bash
python main.py -T 2 -p http://127.0.0.1:8080 https://target.com
```

## Timing Profiles Reference
* `-T 0`: Concurrency: 1, Delay: 5.0s (Very slow, maximum safety)
* `-T 1`: Concurrency: 2, Delay: 2.0s (Slow, safe for restrictive environments)
* `-T 2`: Concurrency: 5, Delay: 1.0s (Moderate)
* `-T 3`: Concurrency: 10, Delay: 0.5s (Default, optimized for speed and stability)
* `-T 4`: Concurrency: 20, Delay: 0.1s (Aggressive, high chance of blocking)
* `-T 5`: Concurrency: 50, Delay: 0.0s (Unrestricted, use only in local/CTF environments)

## Legal Disclaimer
This tool is developed for educational and authorized security testing purposes only. Usage of this tool against targets without prior mutual consent is illegal. It is the end user's responsibility to obey all applicable local, state, and federal laws. The developers assume no liability and are not responsible for any misuse or damage caused by this program. Ensure your activities comply with the target's Vulnerability Disclosure Program (VDP) or Bug Bounty Rules of Engagement (RoE) prior to execution.
