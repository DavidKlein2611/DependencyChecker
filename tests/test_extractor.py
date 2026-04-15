import pytest
from extractor import Extractor

@pytest.fixture
def extractor():
    return Extractor()

def test_is_likely_internal_whitelist(extractor):
    # Whitelisted packages should return False (not internal)
    assert extractor.is_likely_internal('react') is False
    assert extractor.is_likely_internal('lodash') is False
    assert extractor.is_likely_internal('express') is False

def test_is_likely_internal_relative_paths(extractor):
    # Relative or absolute paths should return False
    assert extractor.is_likely_internal('./components/Button') is False
    assert extractor.is_likely_internal('../utils') is False
    assert extractor.is_likely_internal('/var/www/app') is False
    assert extractor.is_likely_internal('\\windows\\path') is False

def test_is_likely_internal_short_names(extractor):
    # Names shorter than 2 characters should return False
    assert extractor.is_likely_internal('a') is False
    assert extractor.is_likely_internal('') is False

def test_is_likely_internal_minified_ids(extractor):
    # Short alphanumeric strings with at least one uppercase letter (minified IDs) should return False
    assert extractor.is_likely_internal('Kijs') is False
    assert extractor.is_likely_internal('g9Kq') is False
    assert extractor.is_likely_internal('A1') is False
    
    # But if they don't have uppercase or are longer, they might be valid
    assert extractor.is_likely_internal('kijs') is True
    assert extractor.is_likely_internal('Kijs1') is True # Length 5

def test_is_likely_internal_malformed_names(extractor):
    # Dynamic variables, template strings, or malformed names should return False
    assert extractor.is_likely_internal('${dynamic}') is False
    assert extractor.is_likely_internal('pkg!') is False
    assert extractor.is_likely_internal('@scope/pkg/extra') is False # Only one slash allowed in regex
    assert extractor.is_likely_internal('-pkg') is False

def test_is_likely_internal_valid_names(extractor):
    # Valid potential internal packages should return True
    assert extractor.is_likely_internal('my-internal-pkg') is True
    assert extractor.is_likely_internal('@myorg/internal-pkg') is True
    assert extractor.is_likely_internal('company.utils') is True
    assert extractor.is_likely_internal('custom_logger') is True
