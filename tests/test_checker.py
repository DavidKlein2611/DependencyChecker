import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from checker import Checker

class MockResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data

@pytest.fixture
def checker():
    c = Checker(delay=0.0)  # Disable default delay for faster tests
    c.client.get = AsyncMock()
    return c

@pytest.mark.asyncio
async def test_make_request_rate_limiting(checker):
    # Setup mock to return 429 twice, then 200
    checker.client.get.side_effect = [
        MockResponse(429),
        MockResponse(429),
        MockResponse(200)
    ]
    
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        response = await checker._make_request("http://test.com")
        
        assert response is not None
        assert response.status_code == 200
        assert checker.client.get.call_count == 3
        # Should have slept twice (2**0 = 1, 2**1 = 2)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

@pytest.mark.asyncio
async def test_make_request_exhaust_retries(checker):
    # Setup mock to return 429 continuously
    checker.client.get.return_value = MockResponse(429)
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        response = await checker._make_request("http://test.com", retries=3)
        assert response is None
        assert checker.client.get.call_count == 3

@pytest.mark.asyncio
async def test_check_npm_safe(checker):
    checker.client.get.return_value = MockResponse(200)
    result = await checker.check_npm("lodash")
    assert result == "Found (Safe)"

@pytest.mark.asyncio
async def test_check_npm_vulnerable(checker):
    checker.client.get.return_value = MockResponse(404)
    result = await checker.check_npm("internal-company-pkg")
    assert result == "Not Found (Potentially Vulnerable)"

@pytest.mark.asyncio
async def test_check_npm_error(checker):
    checker.client.get.return_value = MockResponse(500)
    result = await checker.check_npm("lodash")
    assert result == "Error (500)"

@pytest.mark.asyncio
async def test_check_pypi_scoped(checker):
    # PyPI shouldn't even make a request for scoped packages
    result = await checker.check_pypi("@scope/pkg")
    assert result == "N/A (Scoped)"
    checker.client.get.assert_not_called()

@pytest.mark.asyncio
async def test_check_pypi_safe(checker):
    checker.client.get.return_value = MockResponse(200)
    result = await checker.check_pypi("requests")
    assert result == "Found (Safe)"

@pytest.mark.asyncio
async def test_check_maven_safe(checker):
    checker.client.get.return_value = MockResponse(200, json_data={"response": {"numFound": 1}})
    result = await checker.check_maven("com.company:library")
    assert result == "Found (Safe)"

@pytest.mark.asyncio
async def test_check_maven_vulnerable(checker):
    checker.client.get.return_value = MockResponse(200, json_data={"response": {"numFound": 0}})
    result = await checker.check_maven("com.company:internal-library")
    assert result == "Not Found (Potentially Vulnerable)"

@pytest.mark.asyncio
async def test_check_maven_parse_error(checker):
    # Mock a response where .json() throws an error (e.g. invalid JSON)
    mock_resp = MockResponse(200)
    mock_resp.json = MagicMock(side_effect=Exception("Invalid JSON"))
    checker.client.get.return_value = mock_resp
    result = await checker.check_maven("com.company:library")
    assert result == "Parse Error"

@pytest.mark.asyncio
async def test_check_rubygems_safe(checker):
    checker.client.get.return_value = MockResponse(200)
    result = await checker.check_rubygems("rails")
    assert result == "Found (Safe)"

@pytest.mark.asyncio
async def test_check_package_routing(checker):
    # Verify check_package routes correctly and aggregates results
    checker.client.get.return_value = MockResponse(404)
    result = await checker.check_package(("internal-pkg", "npm"))
    
    assert result['package'] == "internal-pkg"
    assert result['ecosystem'] == "npm"
    assert result['npm_status'] == "Not Found (Potentially Vulnerable)"
    assert result['risk'] == "High"