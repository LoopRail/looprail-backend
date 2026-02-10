from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette import status

from src.api.dependencies import get_current_user, get_wallet_manager_usecase
from src.main import app
from src.models import User
from src.usecases import WalletManagerUsecase
from src.api.dependencies.extra_deps import get_rq_manager
from src.infrastructure.redis import RQManager


@pytest.fixture
def mock_wallet_manager_usecase() -> MagicMock:
    mock = MagicMock(spec=WalletManagerUsecase)
    app.dependency_overrides[get_wallet_manager_usecase] = lambda: mock
    yield mock
    if get_wallet_manager_usecase in app.dependency_overrides:
        del app.dependency_overrides[get_wallet_manager_usecase]


@pytest.fixture
def mock_rq_manager() -> MagicMock:
    mock = MagicMock(spec=RQManager)
    app.dependency_overrides[get_rq_manager] = lambda: mock
    yield mock
    if get_rq_manager in app.dependency_overrides:
        del app.dependency_overrides[get_rq_manager]


@pytest.fixture
def mock_current_user() -> MagicMock:
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid4()
    mock_user.get_prefixed_id.return_value = f"usr_{mock_user.id}"
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield mock_user
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_initiate_withdraw_bank_transfer_success(
    client: TestClient,
    mock_current_user: MagicMock,
    mock_wallet_manager_usecase: MagicMock,
):
    # Arrange
    withdrawal_data = {
        "asset_id": f"ast_{uuid4()}",
        "amount": 100.00,
        "narration": "Test withdrawal",
        "destination": {
            "event": "withdraw:bank-transfer",
            "data": {
                "bank_code": "044",
                "account_number": "1234567890",
                "account_name": "Test User",
            },
        },
    }

    mock_wallet_manager_usecase.initiate_withdrawal.return_value = (
        {"transaction_id": f"txn_{uuid4()}", "status": "pending"},
        None,
    )

    # Act
    response = client.post("/api/v1/wallets/inititate-withdraw", json=withdrawal_data)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["status"] == "pending"
    mock_wallet_manager_usecase.initiate_withdrawal.assert_called_once()


@pytest.mark.asyncio
async def test_initiate_withdraw_invalid_destination(
    client: TestClient,
    mock_current_user: MagicMock,
    mock_wallet_manager_usecase: MagicMock,
):
    # Arrange
    withdrawal_data = {
        "asset_id": f"ast_{uuid4()}",
        "amount": 100.00,
        "narration": "Test withdrawal",
        "destination": {
            "event": "withdraw:invalid-event",
            "data": {},
        },
    }

    # Act
    # Using GenericWithdrawalRequest.to_specific_event internally which might fail validation
    # But let's see how our mock handles it.
    response = client.post("/api/v1/wallets/inititate-withdraw", json=withdrawal_data)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_initiate_withdraw_usecase_error(
    client: TestClient,
    mock_current_user: MagicMock,
    mock_wallet_manager_usecase: MagicMock,
):
    # Arrange
    withdrawal_data = {
        "asset_id": f"ast_{uuid4()}",
        "amount": 100.00,
        "narration": "Test withdrawal",
        "destination": {
            "event": "withdraw:bank-transfer",
            "data": {
                "bank_code": "044",
                "account_number": "1234567890",
                "account_name": "Test User",
            },
        },
    }

    from src.types.error import error

    mock_wallet_manager_usecase.initiate_withdrawal.return_value = (
        None,
        error("Insufficient balance"),
    )

    # Act
    response = client.post("/api/v1/wallets/inititate-withdraw", json=withdrawal_data)

    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == "Insufficient balance"


@pytest.mark.asyncio
async def test_process_withdraw_success(
    client: TestClient,
    mock_current_user: MagicMock,
    mock_rq_manager: MagicMock,
    mock_security_usecase: MagicMock,
    mock_user_usecases: MagicMock,
):
    # Arrange
    from src.api.dependencies import get_current_session
    from src.models import Session
    from uuid import UUID

    session_id_raw = str(uuid4())
    mock_session = MagicMock(spec=Session)
    mock_session.id = UUID(session_id_raw)
    mock_session.get_prefixed_id.return_value = f"ses_{session_id_raw}"
    app.dependency_overrides[get_current_session] = lambda: mock_session

    process_data = {
        "transaction_id": f"txn_{uuid4()}",
        "transation_pin": "123456",
        "challenge_id": "chl_test",
        "code_verifier": "cv_test",
    }

    mock_security_usecase.verify_pkce.return_value = (True, None)
    mock_user_usecases.verify_transaction_pin.return_value = (True, None)

    # Act
    response = client.post("/api/v1/wallets/process-withdraw", json=process_data)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Withdrawal processing initiated successfully."
    mock_rq_manager.get_queue().enqueue.assert_called_once()

    # Clean up
    del app.dependency_overrides[get_current_session]
