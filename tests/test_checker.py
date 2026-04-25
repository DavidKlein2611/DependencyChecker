import pytest
from unittest.mock import AsyncMock, MagicMock
from checker import NpmRegistry, Checker

@pytest.mark.asyncio
async def test_npm_registry_found():
    mock_http_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_http_client.get = AsyncMock(return_value=mock_response)

    registry = NpmRegistry(mock_http_client)

    result = await registry.check("react")

    assert result["npm_status"] == "Found (Safe)"
    mock_http_client.get.assert_called_once_with("https://registry.npmjs.org/react")

@pytest.mark.asyncio
async def test_npm_registry_scoped_unclaimed():
    mock_http_client = AsyncMock()

    mock_scope_response = MagicMock()
    mock_scope_response.status_code = 404

    mock_pkg_response = MagicMock()
    mock_pkg_response.status_code = 404

    mock_http_client.get = AsyncMock(side_effect=[mock_scope_response, mock_pkg_response])

    registry = NpmRegistry(mock_http_client)
    result = await registry.check("@myorg/internal-pkg")

    assert result["scope_status"] == "Unclaimed Scope (Critical)"
    assert result["npm_status"] == "Not Found (Potentially Vulnerable)"

    assert mock_http_client.get.call_count == 2
    mock_http_client.get.assert_any_call("https://registry.npmjs.org/-/org/myorg/package")
    mock_http_client.get.assert_any_call("https://registry.npmjs.org/@myorg/internal-pkg")

@pytest.mark.asyncio
async def test_checker_aggregation_and_routing():
    mock_npm_registry = AsyncMock()
    mock_npm_registry.check = AsyncMock(return_value={
        "npm_status": "Not Found (Potentially Vulnerable)",
        "scope_status": "Unclaimed Scope (Critical)"
    })

    mock_pypi_registry = AsyncMock()
    mock_pypi_registry.check = AsyncMock(return_value={
        "pypi_status": "Found (Safe)"
    })

    adapters = {
        'npm': mock_npm_registry,
        'python': mock_pypi_registry
    }

    checker = Checker(adapters=adapters)

    packages = {("@myorg/internal", "npm"), ("requests", "python")}
    results = await checker.check_packages(packages)

    assert len(results) == 2

    # Verify npm package result
    npm_res = next(r for r in results if r["ecosystem"] == "npm")
    assert npm_res["package"] == "@myorg/internal"
    assert npm_res["risk"] == "Critical"
    assert npm_res["npm_status"] == "Not Found (Potentially Vulnerable)"

    # Verify pypi package result
    pypi_res = next(r for r in results if r["ecosystem"] == "python")
    assert pypi_res["package"] == "requests"
    assert pypi_res["risk"] == "Low"
    assert pypi_res["pypi_status"] == "Found (Safe)"

    # Verify correct routing
    mock_npm_registry.check.assert_called_once_with("@myorg/internal")
    mock_pypi_registry.check.assert_called_once_with("requests")
