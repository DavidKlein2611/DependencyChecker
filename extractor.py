import re
import json

class Extractor:
    def __init__(self):
        # Common patterns for requires or imports
        self.patterns = [
            re.compile(r"""require\(['"]([^.'"][^'"]+)['"]\)"""),
            re.compile(r"""from\s+['"]([^.'"][^'"]+)['"]"""),
            re.compile(r"""import\s+['"]([^.'"][^'"]+)['"]"""),
            re.compile(r"""__webpack_require__\(['"]([^.'"][^'"]+)['"]\)"""),
            re.compile(r"""\/\*\*\*\/\s*['"]([^.'"][^'"]+)['"]\s*:"""),
            re.compile(r"""__vite_ssr_import__\(['"]([^.'"][^'"]+)['"]\)"""),
        ]

        self.whitelist = {
            'react', 'react-dom', 'lodash', 'express', 'axios', 'core-js',
            'jquery', 'vue', 'angular', 'moment', 'tslib', 'rxjs', 'next'
        }

    def is_likely_internal(self, package_name: str) -> bool:
        if package_name in self.whitelist:
            return False
        if package_name.startswith(('.', '/', '\\')):
            return False
        if len(package_name) < 2:
            return False
            
        # Filter out short alphanumeric Webpack/Vite minified module IDs (e.g. 'Kijs', 'g9Kq')
        if len(package_name) <= 4 and package_name.isalnum() and any(c.isupper() for c in package_name):
            return False
            
        # Filter out dynamic variables, template strings (e.g. ${s}), or malformed names
        if not re.match(r"^@?[a-z0-9][a-z0-9._-]*(\/[a-z0-9._-]+)?$", package_name, re.IGNORECASE):
            return False
        return True

    def extract_packages(self, content: str, url: str) -> set[tuple[str, str]]:
        packages = set()

        # Dependency file parsing
        if url.endswith('requirements.txt'):
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('-'): continue
                pkg = re.split(r'[=<>~!]', line)[0].strip()
                if pkg and self.is_likely_internal(pkg): packages.add((pkg, 'python'))
            return packages
            
        if url.endswith('Pipfile'):
            in_packages = False
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('[packages]') or line.startswith('[dev-packages]'):
                    in_packages = True
                    continue
                if line.startswith('['):
                    in_packages = False
                    continue
                if in_packages and '=' in line:
                    pkg = line.split('=')[0].strip().strip('"\'')
                    if pkg and self.is_likely_internal(pkg): packages.add((pkg, 'python'))
            return packages

        if url.endswith('Gemfile'):
            for match in re.findall(r"""gem\s+['"]([^'"]+)['"]""", content):
                if self.is_likely_internal(match): packages.add((match, 'ruby'))
            return packages

        if url.endswith('Gemfile.lock'):
            for match in re.findall(r"^\s{4}([a-zA-Z0-9._-]+)\s*\(", content, re.MULTILINE):
                if self.is_likely_internal(match): packages.add((match, 'ruby'))
            return packages

        if url.endswith('pom.xml'):
            for match in re.findall(r"<artifactId>([^<]+)</artifactId>", content):
                if self.is_likely_internal(match): packages.add((match, 'java'))
            return packages

        if url.endswith('build.gradle'):
            for match in re.findall(r"(?:implementation|api|compile|testImplementation)\s+['\"](?:[^:]+):([^:]+):", content):
                if self.is_likely_internal(match): packages.add((match, 'java'))
            return packages

        # 1. Parse JSON if it's a Source Map (.js.map)
        if url.endswith('.map'):
            try:
                data = json.loads(content)
                for source in data.get('sources', []):
                    if 'node_modules/' in source:
                        parts = source.split('node_modules/')[-1].split('/')
                        pkg_name = f"{parts[0]}/{parts[1]}" if parts[0].startswith('@') and len(parts) > 1 else parts[0]
                        if self.is_likely_internal(pkg_name):
                            packages.add((pkg_name, 'npm'))
            except json.JSONDecodeError:
                pass # Fallback to regex if parsing fails

        # 2. Raw regex for node_modules/ paths in both .js and .map files
        # This catches Webpack chunk dictionaries and Vite registries
        for match in re.findall(r"node_modules/(@[a-z0-9._-]+/[a-z0-9._-]+|[a-z0-9._-]+)", content, re.IGNORECASE):
            if self.is_likely_internal(match):
                packages.add((match, 'npm'))

        # 3. Standard AST-style requires and imports
        for pattern in self.patterns:
            matches = pattern.findall(content)
            for match in matches:
                pkg_name = match.split('/')[0] if not match.startswith('@') else '/'.join(match.split('/')[:2])
                if self.is_likely_internal(pkg_name):
                    packages.add((pkg_name, 'npm'))
        
        return packages

