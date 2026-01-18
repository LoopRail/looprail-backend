from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette import status

from src.api.dependencies import get_current_user, get_wallet_manager_usecase
from src.main import app
from src.models import User
from src.dtos.wallet_dtos import (
    WithdrawalRequest,
    GenericWithdrawalRequest,
    BankTransferData,
    TransferType,
)
from src.types.types import WithdrawalMethod
from src.usecases import WalletManagerUsecase


@pytest.fixture
def mock_wallet_manager_usecase() -> MagicMock:
    mock = MagicMock(spec=WalletManagerUsecase)
    app.dependency_overrides[get_wallet_manager_usecase] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def mock_current_user() -> MagicMock:
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid4()
    mock_user.get_prefixed_id.return_value = f"usr_{mock_user.id}"
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield mock_user
    app.dependency_overrides.clear()


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
                "institution": "Test Bank",
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
