from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_asset_repository,
    get_blockrader_wallet_service,
    get_current_user_token,
    get_ledger_service,
    get_user_usecases,
    get_wallet_repository,
)
from src.infrastructure.repositories import AssetRepository, WalletRepository
from src.infrastructure.services import LedgerService
from src.main import app
from src.models import User
from src.models.wallet_model import Asset, Wallet
from src.types import AccessToken, AssetType, TokenType, Gender, error
from src.usecases import WalletService


@pytest.fixture
def mock_deps():
    mock_user_usecase = AsyncMock()
    mock_wallet_service = AsyncMock(spec=WalletService)

    return {
        "user_usecase": mock_user_usecase,
        "wallet_service": mock_wallet_service,
    }


@pytest.mark.asyncio
async def test_get_user_account_success(mock_deps):
    user_id = uuid4()
    wallet_id = uuid4()

    # Mock User
    user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        username="testuser",
        is_email_verified=True,
        has_completed_onboarding=True,
        gender=Gender.MALE,
        ledger_identity_id="ledger_123",
    )
    mock_deps["user_usecase"].get_user_by_id.return_value = (user, None)

    # Mock Wallet Output
    mock_deps["wallet_service"].get_wallet_with_assets.return_value = (
        {
            "id": f"wlt_{wallet_id}",
            "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "chain": "ethereum",
            "provider": "paycrest",
            "is-active": True,
            "assets": [
                {
                    "asset-id": "ast_123",
                    "name": "USDT",
                    "symbol": "USDT",
                    "decimals": 18,
                    "asset-type": "usdt",
                    "balance": "1.0",
                    "network": "mainnet",
                    "address": "0x...",
                    "is-active": True,
                }
            ],
        },
        None,
    )

    # Token
    token = AccessToken(
        sub="access_ses_123",
        user_id=f"usr_{user_id}",
        token_type=TokenType.ACCESS_TOKEN,
        session_id="ses_123",
        platform="web",
    )

    # Overrides
    app.dependency_overrides[get_current_user_token] = lambda: token
    app.dependency_overrides[get_user_usecases] = lambda: mock_deps["user_usecase"]
    app.dependency_overrides[get_blockrader_wallet_service] = lambda: mock_deps[
        "wallet_service"
    ]

    with TestClient(app) as client:
        response = client.get("/api/v1/account/me")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "test@example.com"
    assert data["wallet"]["address"] == "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    assert len(data["wallet"]["assets"]) == 1
    assert data["wallet"]["assets"][0]["symbol"] == "USDT"

    # Cleanup
    app.dependency_overrides.clear()
