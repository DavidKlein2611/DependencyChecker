import json
from urllib.parse import urlparse

class Reporter:
    def generate_report(self, findings: list[dict], url: str, save_json: bool = False):
        print("\n" + "="*50)
        print("Dependency Confusion Scan Report")
        print("="*50)
        
        critical_risk = [f for f in findings if f['risk'] == 'Critical']
        high_risk = [f for f in findings if f['risk'] == 'High']
        
        print(f"Target: {url}")
        print(f"Total Packages Checked: {len(findings)}")
        print(f"Critical Risk (Scope Takeover) Found: {len(critical_risk)}")
        print(f"High Risk Packages Found: {len(high_risk)}")
        print("-" * 50)
        
        for finding in findings:
            if finding['risk'] == 'Critical':
                risk_indicator = "[!!!]"
            elif finding['risk'] == 'High':
                risk_indicator = "[!]"
            else:
                risk_indicator = "[i]"
                
            print(f"{risk_indicator} Package: {finding['package']}")
            print(f"    NPM:   {finding['npm_status']}")
            if finding['scope_status'] != 'N/A':
                print(f"    Scope: {finding['scope_status']}")
            print(f"    PyPI:  {finding['pypi_status']}")
            
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
                        'critical_risk_found': len(critical_risk),
                        'high_risk_found': len(high_risk)
                    },
                    'findings': findings
                }, f, indent=4)
                
            print(f"[+] Report saved to {report_filename}")
