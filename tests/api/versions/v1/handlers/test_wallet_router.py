from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from starlette import status

from src.api.versions.v1.handlers.wallet_router import withdraw_auth_lock
from src.api.rate_limiters.rate_limiter import get_custom_rate_limiter
from src.api.dependencies import (
    get_current_user,
    get_wallet_manager_usecase,
    get_config,
    get_user_usecases,
)
from src.api.dependencies.extra_deps import get_rq_manager
from src.api.rate_limiters.rate_limiter import get_custom_rate_limiter
from src.main import app
from src.models import User
from src.infrastructure.config_settings import Config
from src.infrastructure.redis import RQManager
from src.infrastructure.services import AuthLockService
from src.usecases import UserUseCase, WalletManagerUsecase


@pytest.fixture
def mock_wallet_manager() -> MagicMock:
    return MagicMock(spec=WalletManagerUsecase)


@pytest.fixture
def mock_rq_manager() -> MagicMock:
    return MagicMock(spec=RQManager)


@pytest.fixture
def mock_user_usecase() -> MagicMock:
    return MagicMock(spec=UserUseCase)


@pytest.fixture
def mock_auth_lock_service() -> MagicMock:
    return MagicMock(spec=AuthLockService)


@pytest.fixture
def mock_custom_limiter() -> MagicMock:
    mock = MagicMock()
    mock.check_limit = AsyncMock(return_value=(True, "", 0, None))
    return mock


@pytest.fixture
def mock_current_user() -> MagicMock:
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid4()
    mock_user.email = "test@example.com"
    mock_user.get_prefixed_id.return_value = f"usr_{mock_user.id}"
    return mock_user


@pytest.fixture
def mock_config() -> MagicMock:
    mock = MagicMock()
    # Mocking block_rader.wallets.wallets[0].wallet_id etc.
    mock_block_rader = MagicMock()
    mock_block_rader.wallets = MagicMock()
    mock_block_rader.wallets.wallets = [MagicMock(wallet_id="wallet_123")]
    mock.block_rader = mock_block_rader

    mock_ledger = MagicMock()
    mock_ledger.ledgers = MagicMock()
    mock_ledger.ledgers.ledgers = [MagicMock(ledger_id="ledger_123")]
    mock.ledger = mock_ledger
    return mock


@pytest.mark.asyncio
async def test_withdraw_success(
    mock_current_user,
    mock_wallet_manager,
    mock_rq_manager,
    mock_user_usecase,
    mock_auth_lock_service,
    mock_config,
    mock_custom_limiter,
):
    # Setup mocks
    mock_auth_lock_service.is_account_locked = AsyncMock(return_value=(False, None))
    mock_user_usecase.verify_transaction_pin = AsyncMock(return_value=(True, None))
    mock_auth_lock_service.reset_failed_attempts = AsyncMock()
    
    mock_wallet_manager.initiate_withdrawal = AsyncMock(return_value=({"transaction_id": "txn_123"}, None))
    
    # Payload
    withdrawal_data = {
        "asset_id": f"ast_{uuid4()}",
        "amount": 100.0,
        "currency": "usd",
        "narration": "Test withdrawal",
        "destination": {
            "event": "withdraw:bank-transfer",
            "data": {
                "bank_code": "044",
                "account_number": "1234567890",
                "account_name": "Test User",
            },
        },
        "authorization": {
            "authorizationMethod": 1,
            "localTime": 123456789,
            "pin": "123456",
            "amount": 100,
        }
    }

    # Dependency Overrides
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    app.dependency_overrides[get_wallet_manager_usecase] = lambda: mock_wallet_manager
    app.dependency_overrides[get_config] = lambda: mock_config
    app.dependency_overrides[get_rq_manager] = lambda: mock_rq_manager
    app.dependency_overrides[get_user_usecases] = lambda: mock_user_usecase
    app.dependency_overrides[withdraw_auth_lock] = lambda: mock_auth_lock_service
    app.dependency_overrides[get_custom_rate_limiter] = lambda: mock_custom_limiter

    with TestClient(app) as client:
        response = client.post("/api/v1/wallets/withdraw", json=withdrawal_data)

    # Assertions
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Withdrawal processing initiated successfully."
    
    mock_auth_lock_service.is_account_locked.assert_called_once_with(mock_current_user.email)
    mock_user_usecase.verify_transaction_pin.assert_called_once()
    mock_wallet_manager.initiate_withdrawal.assert_called_once()
    mock_rq_manager.get_queue().enqueue.assert_called_once()

    # Cleanup
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_withdraw_invalid_pin(
    mock_current_user,
    mock_wallet_manager,
    mock_rq_manager,
    mock_user_usecase,
    mock_auth_lock_service,
    mock_config,
    mock_custom_limiter,
):
    # Setup mocks
    mock_auth_lock_service.is_account_locked = AsyncMock(return_value=(False, None))
    mock_user_usecase.verify_transaction_pin = AsyncMock(return_value=(False, None))
    mock_auth_lock_service.increment_failed_attempts = AsyncMock(return_value=(1, None))
    
    # Payload
    withdrawal_data = {
        "asset_id": f"ast_{uuid4()}",
        "amount": 100.0,
        "currency": "usd",
        "narration": "Test withdrawal",
        "destination": {
            "event": "withdraw:bank-transfer",
            "data": {
                "bank_code": "044",
                "account_number": "1234567890",
                "account_name": "Test User",
            },
        },
        "authorization": {
            "authorizationMethod": 1,
            "localTime": 123456789,
            "pin": "wrong_pin",
            "amount": 100,
        }
    }

    # Dependency Overrides
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    app.dependency_overrides[get_wallet_manager_usecase] = lambda: mock_wallet_manager
    app.dependency_overrides[get_config] = lambda: mock_config
    app.dependency_overrides[get_rq_manager] = lambda: mock_rq_manager
    app.dependency_overrides[get_user_usecases] = lambda: mock_user_usecase
    app.dependency_overrides[withdraw_auth_lock] = lambda: mock_auth_lock_service
    app.dependency_overrides[get_custom_rate_limiter] = lambda: mock_custom_limiter

    with TestClient(app) as client:
        response = client.post("/api/v1/wallets/withdraw", json=withdrawal_data)

    # Assertions
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["message"] == "Invalid transaction PIN"
    
    mock_auth_lock_service.increment_failed_attempts.assert_called_once_with(mock_current_user.email)

    # Cleanup
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_withdraw_account_locked(
    mock_current_user,
    mock_wallet_manager,
    mock_rq_manager,
    mock_user_usecase,
    mock_auth_lock_service,
    mock_config,
    mock_custom_limiter,
):
    # Setup mocks
    mock_auth_lock_service.is_account_locked = AsyncMock(return_value=(True, None))
    
    # Payload
    withdrawal_data = {
        "asset_id": f"ast_{uuid4()}",
        "amount": 100.0,
        "currency": "usd",
        "narration": "Test withdrawal",
        "destination": {
            "event": "withdraw:bank-transfer",
            "data": {
                "bank_code": "044",
                "account_number": "1234567890",
                "account_name": "Test User",
            },
        },
        "authorization": {
            "authorizationMethod": 1,
            "localTime": 123456789,
            "pin": "123456",
            "amount": 100,
        }
    }

    # Dependency Overrides
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    app.dependency_overrides[get_wallet_manager_usecase] = lambda: mock_wallet_manager
    app.dependency_overrides[get_config] = lambda: mock_config
    app.dependency_overrides[get_rq_manager] = lambda: mock_rq_manager
    app.dependency_overrides[get_user_usecases] = lambda: mock_user_usecase
    app.dependency_overrides[withdraw_auth_lock] = lambda: mock_auth_lock_service
    app.dependency_overrides[get_custom_rate_limiter] = lambda: mock_custom_limiter

    with TestClient(app) as client:
        response = client.post("/api/v1/wallets/withdraw", json=withdrawal_data)

    # Assertions
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["message"] == "Account is locked due to too many failed attempts."

    # Cleanup
    app.dependency_overrides.clear()

