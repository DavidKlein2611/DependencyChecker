import pytest
from extractor import Extractor

def test_extract_requirements_txt():
    extractor = Extractor()
    content = """
requests==2.31.0
# a comment
pytest>=7.4.0
"""
    packages = extractor.extract_packages(content, 'https://example.com/requirements.txt')

    assert ('requests', 'python') in packages
    assert ('pytest', 'python') in packages

def test_extract_ruby_gemfile():
    extractor = Extractor()
    content = """
source "https://rubygems.org"
gem "rails", "~> 7.0.0"
gem 'pg'
"""
    packages = extractor.extract_packages(content, 'https://example.com/Gemfile')
    assert ('rails', 'ruby') in packages
    assert ('pg', 'ruby') in packages

def test_extract_java_pom():
    extractor = Extractor()
    content = """
<project>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
    </dependencies>
</project>
"""
    packages = extractor.extract_packages(content, 'https://example.com/pom.xml')
    assert ('spring-boot-starter-web', 'java') in packages

def test_extract_npm_js_map():
    extractor = Extractor()
    content = '{"version":3,"sources":["webpack:///node_modules/axios/index.js","webpack:///node_modules/@myorg/internal-pkg/utils.js"]}'
    packages = extractor.extract_packages(content, 'https://example.com/app.js.map')
    # axios should be ignored because it is in the whitelist
    assert ('axios', 'npm') not in packages
    assert ('@myorg/internal-pkg', 'npm') in packages

def test_extract_npm_js_requires():
    extractor = Extractor()
    content = """
    const _ = require('lodash');
    const myLib = require('@company/mylib');
    import { something } from 'external-lib';
    """
    packages = extractor.extract_packages(content, 'https://example.com/app.js')
    # lodash should be ignored (whitelist)
    assert ('lodash', 'npm') not in packages
    assert ('@company/mylib', 'npm') in packages
    assert ('external-lib', 'npm') in packages
