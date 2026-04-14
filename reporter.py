import json
from urllib.parse import urlparse

class Reporter:
    def generate_report(self, findings: list[dict], url: str, save_json: bool = False):
        print("\n" + "="*50)
        print("Dependency Confusion Scan Report")
        print("="*50)
        
        high_risk = [f for f in findings if f['risk'] == 'High']
        
        print(f"Target: {url}")
        print(f"Total Packages Checked: {len(findings)}")
        print(f"High Risk Packages Found: {len(high_risk)}")
        print("-" * 50)
        
        for finding in findings:
            risk_indicator = "[!]" if finding['risk'] == 'High' else "[i]"
            print(f"{risk_indicator} Package: {finding['package']}")
            print(f"    NPM:  {finding['npm_status']}")
            print(f"    PyPI: {finding['pypi_status']}")
            
        print("="*50 + "\n")
        
        if save_json:
            # Save to file
            domain = urlparse(url).netloc
            report_filename = f"report_{domain.replace(':', '_')}.json"
            
            with open(report_filename, 'w') as f:
                json.dump({
                    'target': url,
                    'summary': {
                        'total_checked': len(findings),
                        'high_risk_found': len(high_risk)
                    },
                    'findings': findings
                }, f, indent=4)
                
            print(f"[+] Report saved to {report_filename}")
