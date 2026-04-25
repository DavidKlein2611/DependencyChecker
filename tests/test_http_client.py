import pytest
from unittest.mock import AsyncMock, patch
from http_client import HTTPClient

@pytest.mark.asyncio
async def test_basic_fetch():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = 'success'

    with patch('http_client.requests.AsyncSession') as MockSession:
        mock_instance = MockSession.return_value
        mock_instance.get = AsyncMock(return_value=mock_response)
        
        client = HTTPClient(delay=0)
        response = await client.get('https://example.com')
        
        assert response is not None
        assert response.status_code == 200
        assert response.text == 'success'
        mock_instance.get.assert_called_once_with('https://example.com')

@pytest.mark.asyncio
async def test_retry_on_429():
    mock_429 = AsyncMock()
    mock_429.status_code = 429
    
    mock_200 = AsyncMock()
    mock_200.status_code = 200
    
    with patch('http_client.requests.AsyncSession') as MockSession:
        mock_instance = MockSession.return_value
        mock_instance.get = AsyncMock(side_effect=[mock_429, mock_200])
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            client = HTTPClient(delay=0)
            response = await client.get('https://example.com', retries=3)
            
            assert response is not None
            assert response.status_code == 200
            assert mock_instance.get.call_count == 2

@pytest.mark.asyncio
async def test_network_error_returns_none():
    with patch('http_client.requests.AsyncSession') as MockSession:
        mock_instance = MockSession.return_value
        from curl_cffi.requests.errors import RequestsError
        mock_instance.get = AsyncMock(side_effect=RequestsError('Connection refused'))
        
        client = HTTPClient(delay=0)
        response = await client.get('https://example.com')
        
        assert response is None
