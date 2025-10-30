from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.settings import otp_config
from src.usecases import OtpUseCase
from tests.mocks.mock_redis import MockRedisClient


@pytest.fixture
def mock_redis_client():
    return MockRedisClient()


@pytest.fixture
def otp_usecase(mock_redis_client):
    return OtpUseCase(mock_redis_client, otp_config)


@pytest.mark.asyncio
async def test_generate_otp_success(otp_usecase, mock_redis_client):
    email = "test@example.com"
    otp_code, otp_token, err = await otp_usecase.generate_otp(email)

    assert err is None
    assert otp_code is not None
    assert otp_token is not None
    assert len(otp_code) == 6
    assert len(otp_token) > 0

    # Verify that the OTP and token are stored in Redis
    token, get_err = await mock_redis_client.get(f"otp:email:{email}")
    assert get_err is None
    assert token is not None
    assert token == otp_token


@pytest.mark.asyncio
async def test_generate_otp_redis_failure(otp_usecase, mock_redis_client):
    email = "test@example.com"

    # Simulate Redis create failure
    async def mock_create(key, data, ttl):
        return MagicMock(message="Redis create failed")  # Return an error object

    mock_redis_client.create = AsyncMock(side_effect=mock_create)

    otp_code, otp_token, err = await otp_usecase.generate_otp(email)

    assert err is not None
    assert err.message == "Redis create failed"
    assert otp_code is None
    assert otp_token is None

    # Verify that nothing was stored in Redis
    stored_data, get_err = await mock_redis_client.get(f"otp:email:{email}")
    assert get_err is not None
    assert stored_data is None
