from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_asset_repository,
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
from src.types import AccessToken, AssetType, TokenType, Gender


@pytest.fixture
def mock_deps():
    mock_user_usecase = AsyncMock()
    mock_wallet_repo = AsyncMock(spec=WalletRepository)
    mock_asset_repo = AsyncMock(spec=AssetRepository)
    mock_ledger_service = MagicMock(spec=LedgerService)

    # Mock ledger balances
    mock_ledger_service.balances = AsyncMock()

    return {
        "user_usecase": mock_user_usecase,
        "wallet_repo": mock_wallet_repo,
        "asset_repo": mock_asset_repo,
        "ledger_service": mock_ledger_service,
    }


@pytest.mark.asyncio
async def test_get_user_account_success(mock_deps):
    user_id = uuid4()
    wallet_id = uuid4()
    asset_id = uuid4()

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

    # Mock Wallet
    wallet = Wallet(
        id=wallet_id,
        user_id=user_id,
        address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        chain="ethereum",
        provider="paycrest",
        ledger_id="ledger_123",
    )
    mock_deps["wallet_repo"].get_wallet_by_user_id.return_value = (wallet, None)

    # Mock Assets
    asset = Asset(
        id=asset_id,
        wallet_id=wallet_id,
        ledger_balance_id="bal_123",
        name="Ethereum",
        asset_id=uuid4(),
        asset_type=AssetType.USDT,
        address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        symbol="USDT",
        decimals=18,
        network="mainnet",
    )
    mock_deps["asset_repo"].get_assets_by_wallet_id.return_value = ([asset], None)

    # Mock Ledger Balance
    balance_response = MagicMock()
    balance_response.balance = 1000000000000000000  # 1 ETH
    balance_response.available_balance = 1000000000000000000
    mock_deps["ledger_service"].balances.get_balance.return_value = (
        balance_response,
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
    app.dependency_overrides[get_wallet_repository] = lambda: mock_deps["wallet_repo"]
    app.dependency_overrides[get_asset_repository] = lambda: mock_deps["asset_repo"]
    app.dependency_overrides[get_ledger_service] = lambda: mock_deps["ledger_service"]

    with TestClient(app) as client:
        response = client.get("/api/v1/account/me")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "test@example.com"
    assert data["wallet"]["address"] == "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    assert len(data["wallet"]["assets"]) == 1
    assert data["wallet"]["assets"][0]["symbol"] == "USDT"
    assert data["wallet"]["assets"][0]["balance"] == "1000000000000000000"

    # Cleanup
    app.dependency_overrides.clear()
@pytest.mark.asyncio
async def test_get_user_balance_success(mock_deps):
    user_id = uuid4()
    wallet_id = uuid4()
    asset_id = uuid4()

    # Mock Wallet
    wallet = Wallet(
        id=wallet_id,
        user_id=user_id,
        address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        chain="ethereum",
        provider="paycrest",
        ledger_id="ledger_123",
    )
    mock_deps["wallet_repo"].get_wallet_by_user_id.return_value = (wallet, None)

    # Mock Assets
    asset = Asset(
        id=asset_id,
        wallet_id=wallet_id,
        ledger_balance_id="bal_123",
        name="Ethereum",
        asset_id=uuid4(),
        asset_type=AssetType.USDT,
        address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        symbol="USDT",
        decimals=18,
        network="mainnet",
    )
    mock_deps["asset_repo"].get_assets_by_wallet_id.return_value = ([asset], None)

    # Mock Ledger Balance
    balance_response = MagicMock()
    balance_response.balance = 1000000000000000000  # 1 ETH
    balance_response.available_balance = 1000000000000000000
    mock_deps["ledger_service"].balances.get_balance.return_value = (
        balance_response,
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
    app.dependency_overrides[get_wallet_repository] = lambda: mock_deps["wallet_repo"]
    app.dependency_overrides[get_asset_repository] = lambda: mock_deps["asset_repo"]
    app.dependency_overrides[get_ledger_service] = lambda: mock_deps["ledger_service"]

    with TestClient(app) as client:
        response = client.get("/api/v1/account/balance")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["address"] == "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    assert len(data["assets"]) == 1
    assert data["assets"][0]["symbol"] == "USDT"
    assert data["assets"][0]["balance"] == "1000000000000000000"

    # Cleanup
    app.dependency_overrides.clear()
