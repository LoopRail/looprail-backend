import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_config,
    get_lock_service,
    get_transaction_usecase,
    get_verify_webhook_request,
    get_session_repository,
    get_notification_usecase,
    get_user_repository,
    get_resend_service,
)
from src.api.dependencies.repositories import (
    get_asset_repository,
    get_wallet_repository,
    get_transaction_repository,
)
from src.api.dependencies.services import get_ledger_service
from src.infrastructure.settings import ENVIRONMENT
from src.main import app
from src.types.common_types import Network

@pytest.fixture
def client():
    # Setup app state essentials for tests to handle direct state access if any
    app.state.ledger_service = MagicMock()
    app.state.resend = MagicMock()
    app.state.rq_manager = MagicMock()
    return TestClient(app)

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.app.environment = ENVIRONMENT.PRODUCTION
    return config

@pytest.fixture
def base_payload():
    now = datetime.now(timezone.utc)
    return {
        "event": "deposit.success",
        "data": {
            "id": "evt_123",
            "reference": "ref_123",
            "status": "SUCCESS",
            "type": "DEPOSIT",
            "network": Network.TESTNET,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
            "amount": "100.00",
            "amountPaid": "100.00",
            "currency": "USDC",
            "senderAddress": "0x0987654321098765432109876543210987654321",
            "recipientAddress": "0x1234567890123456789012345678901234567890",
            "confirmations": 1,
            "confirmed": True,
            "amlScreening": {
                "status": "cleared",
                "message": "Cleared",
                "provider": "ComplyCube",
            },
            "asset": {
                "id": "asset_123",
                "name": "USDC",
                "symbol": "USDC",
                "network": Network.TESTNET,
                "decimals": 6,
                "address": "0x1234567890123456789012345678901234567890",
                "isActive": True,
                "logoUrl": "http://example.com/logo.png",
                "standard": "ERC20"
            },
            "blockchain": {
                "id": "eth_id",
                "name": "Ethereum",
                "symbol": "ETH",
                "slug": "ethereum",
                "isActive": True,
                "isEvmCompatible": True,
                "logoUrl": "http://example.com/eth.png",
                "derivationPath": "m/44/60/0/0/0",
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
                "tokenStandard": "ERC20"
            },
            "wallet": {
                "id": "wallet_123",
                "address": "0x1234567890123456789012345678901234567890",
                "name": "My Wallet",
                "network": Network.TESTNET,
                "isActive": True,
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
                "derivationPath": "m/44/60/0/0/0"
            }
        },
    }

@pytest.mark.asyncio
async def test_route_ignores_testnet_in_production(client, mock_config, base_payload):
    # Setup mocks
    mock_config.app.environment = ENVIRONMENT.PRODUCTION
    base_payload["data"]["network"] = Network.TESTNET
    
    app.dependency_overrides[get_config] = lambda: mock_config
    app.dependency_overrides[get_verify_webhook_request] = lambda: AsyncMock()
    
    # We want to verify that get_registry is NOT called or something similar
    # But more simply, we can patch get_registry to see if it's accessed
    with patch("src.api.versions.v1.handlers.webhook_router.get_registry") as mock_get_registry:
        response = client.post("/api/v1/webhooks/blockrader", json=base_payload)
        
        assert response.status_code == 200
        assert response.json()["message"] == "Webhook ignored in production environment"
        mock_get_registry.assert_not_called()
    
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_route_allows_mainnet_in_production(client, mock_config, base_payload):
    mock_config.app.environment = ENVIRONMENT.PRODUCTION
    base_payload["data"]["network"] = Network.MAINNET
    
    app.dependency_overrides[get_config] = lambda: mock_config
    app.dependency_overrides[get_verify_webhook_request] = lambda: AsyncMock()
    
    # Required for the registry path (to avoid other crashes)
    app.dependency_overrides[get_ledger_service] = lambda: MagicMock()
    app.dependency_overrides[get_wallet_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_asset_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_transaction_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_transaction_usecase] = lambda: MagicMock()
    app.dependency_overrides[get_lock_service] = lambda: MagicMock()
    app.dependency_overrides[get_session_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_notification_usecase] = lambda: MagicMock()
    app.dependency_overrides[get_user_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_resend_service] = lambda: MagicMock()

    with patch("src.api.versions.v1.handlers.webhook_router.get_registry") as mock_get_registry:
        # Mock register to return a mock and handler
        mock_handler = AsyncMock()
        mock_get_registry.return_value.get.return_value = mock_handler
        
        response = client.post("/api/v1/webhooks/blockrader", json=base_payload)
        
        assert response.status_code == 200
        mock_get_registry.assert_called_once()
        mock_handler.assert_called_once()
    
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_route_allows_testnet_in_staging(client, mock_config, base_payload):
    mock_config.app.environment = ENVIRONMENT.STAGING
    base_payload["data"]["network"] = Network.TESTNET
    
    app.dependency_overrides[get_config] = lambda: mock_config
    app.dependency_overrides[get_verify_webhook_request] = lambda: AsyncMock()
    
    # Required for the registry path
    app.dependency_overrides[get_ledger_service] = lambda: MagicMock()
    app.dependency_overrides[get_wallet_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_asset_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_transaction_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_transaction_usecase] = lambda: MagicMock()
    app.dependency_overrides[get_lock_service] = lambda: MagicMock()
    app.dependency_overrides[get_session_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_notification_usecase] = lambda: MagicMock()
    app.dependency_overrides[get_user_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_resend_service] = lambda: MagicMock()

    with patch("src.api.versions.v1.handlers.webhook_router.get_registry") as mock_get_registry:
        mock_handler = AsyncMock()
        mock_get_registry.return_value.get.return_value = mock_handler
        
        response = client.post("/api/v1/webhooks/blockrader", json=base_payload)
        
        assert response.status_code == 200
        mock_get_registry.assert_called_once()
        mock_handler.assert_called_once()
    
    app.dependency_overrides = {}
