import json
from urllib.parse import urlparse
from rich.console import Console
from rich.table import Table

class Reporter:
    def __init__(self):
        self.console = Console()

    def generate_report(self, findings: list[dict], url: str, save_json: bool = False):
        self.console.print("\n[bold cyan]" + "="*60 + "[/bold cyan]")
        self.console.print("[bold white]Dependency Confusion Scan Report[/bold white]", justify="center")
        self.console.print("[bold cyan]" + "="*60 + "[/bold cyan]\n")
        
        critical_risk = [f for f in findings if f['risk'] == 'Critical']
        high_risk = [f for f in findings if f['risk'] == 'High']
        
        self.console.print(f"[bold]Target:[/bold] [blue]{url}[/blue]")
        self.console.print(f"[bold]Total Packages Checked:[/bold] {len(findings)}")
        self.console.print(f"[bold red]Critical Risk (Scope Takeover) Found:[/bold red] {len(critical_risk)}")
        self.console.print(f"[bold yellow]High Risk Packages Found:[/bold yellow] {len(high_risk)}\n")
        
        if findings:
            table = Table(show_header=True, header_style="bold magenta", expand=True)
            table.add_column("Risk", width=12, justify="center")
            table.add_column("Package", style="bold")
            table.add_column("Ecosystem", justify="center")
            table.add_column("Details")
            
            for finding in findings:
                if finding['risk'] == 'Critical':
                    risk_display = "[bold red blink]!!! Critical !!![/bold red blink]"
                elif finding['risk'] == 'High':
                    risk_display = "[bold yellow]! High ![/bold yellow]"
                else:
                    risk_display = "[green]Low[/green]"
                    
                details = []
                if finding['ecosystem'] == 'npm':
                    details.append(f"NPM: {finding['npm_status']}")
                    if finding['scope_status'] != 'N/A':
                        details.append(f"Scope: {finding['scope_status']}")
                elif finding['ecosystem'] == 'python':
                    details.append(f"PyPI: {finding['pypi_status']}")
                elif finding['ecosystem'] == 'ruby':
                    details.append(f"RubyGems: {finding['ruby_status']}")
                elif finding['ecosystem'] == 'java':
                    details.append(f"Maven: {finding['java_status']}")
                
                table.add_row(
                    risk_display, 
                    finding['package'], 
                    finding['ecosystem'], 
                    "\n".join(details)
                )
                
            self.console.print(table)
        else:
            self.console.print("[yellow]No dependencies found or checked.[/yellow]")
            
        self.console.print("\n[bold cyan]" + "="*60 + "[/bold cyan]\n")
        
        if save_json:
            domain = urlparse(url).netloc
            report_filename = f"report_{domain.replace(':', '_')}.json"
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'target': url,
                    'summary': {
                        'total_checked': len(findings),
                        'critical_risk_found': len(critical_risk),
                        'high_risk_found': len(high_risk)
                    },
                    'findings': findings
                }, f, indent=4)
                
            self.console.print(f"[bold green][+][/bold green] Report saved to [bold]{report_filename}[/bold]")