import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from src.api.rate_limiters.limiters import CustomRateLimiter
from src.infrastructure.redis import RedisError
from src.infrastructure.services import RedisClient

@pytest.fixture
def mock_redis():
    mock = MagicMock()
    return mock

@pytest.fixture
def limiter(mock_redis):
    client = MagicMock(spec=RedisClient)
    client._instance = mock_redis
    return CustomRateLimiter(client)

@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.client.host = "127.0.0.1"
    return request

@pytest.mark.asyncio
async def test_check_email_limit_success(limiter, mock_redis):
    mock_redis.zremrangebyscore = AsyncMock()
    mock_redis.zcard = AsyncMock(return_value=2)
    mock_redis.zadd = AsyncMock()
    mock_redis.expire = AsyncMock()
    
    allowed, error = await limiter._check_email_limit("otp", "test@example.com")
    
    assert allowed is True
    assert error is None
    mock_redis.zadd.assert_called_once()

@pytest.mark.asyncio
async def test_check_email_limit_exceeded(limiter, mock_redis):
    mock_redis.zremrangebyscore = AsyncMock()
    mock_redis.zcard = AsyncMock(return_value=5) # Limit is 5 for otp
    
    allowed, error = await limiter._check_email_limit("otp", "test@example.com")
    
    assert allowed is False
    assert "Maximum 5 requests" in error

@pytest.mark.asyncio
async def test_check_email_limit_redis_error_fallback(limiter, mock_redis):
    mock_redis.zremrangebyscore = AsyncMock(side_effect=RedisError("Connection failed"))
    
    # Should fallback to True (fail-open)
    allowed, error = await limiter._check_email_limit("otp", "test@example.com")
    
    assert allowed is True
    assert error is None

@pytest.mark.asyncio
async def test_check_ip_limit_redis_error_fallback(limiter, mock_redis):
    mock_redis.hgetall = AsyncMock(side_effect=RedisError("Timeout"))
    
    allowed, error, retry_after = await limiter._check_ip_limit("otp", "127.0.0.1")
    
    assert allowed is True
    assert error is None
    assert retry_after is None

@pytest.mark.asyncio
async def test_check_global_limit_success(limiter, mock_redis):
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock()
    
    allowed, error = await limiter._check_global_limit("otp")
    
    assert allowed is True
    mock_redis.incr.assert_called_once()

@pytest.mark.asyncio
async def test_check_global_limit_exceeded(limiter, mock_redis):
    mock_redis.incr = AsyncMock(return_value=1001) # otp limit is 1000
    
    allowed, error = await limiter._check_global_limit("otp")
    
    assert allowed is False
    assert "high load" in error
