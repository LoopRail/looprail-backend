from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.dependencies import get_config
from src.api.dependencies.repositories import (get_asset_repository,
                                               get_wallet_repository)
from src.api.dependencies.services import get_ledger_service
from src.api.dependencies.usecases import get_transaction_usecase
from src.infrastructure.repositories import AssetRepository, WalletRepository
from src.main import app
from src.models import Asset, User, Wallet
from src.types.types import AssetType
from src.usecases import TransactionUsecase


@pytest.fixture
def mock_wallet():
    return Wallet(
        id=uuid4(),
        user_id=uuid4(),
        address="0x1234567890123456789012345678901234567890",
        chain="base",
        provider="blockrader",
        ledger_id="ledger_123",
    )


@pytest.fixture
def mock_asset(mock_wallet):
    return Asset(
        id=uuid4(),
        wallet_id=mock_wallet.id,
        ledger_balance_id="bal_123",
        name="Solana",
        asset_id=uuid4(),
        asset_type=AssetType.cNGN,  # Use valid AssetType
        address="0x1234567890123456789012345678901234567890",
        symbol="NGN",
        decimals=2,
        network="mainnet",
    )


@pytest.mark.asyncio
async def test_webhook_deposit_success_country_detection(
    client, mock_wallet, mock_asset, mock_config
):
    # Setup mocks
    mock_wallet_repo = AsyncMock(spec=WalletRepository)
    mock_wallet_repo.get_wallet_by_address.return_value = (mock_wallet, None)

    mock_asset_repo = AsyncMock(spec=AssetRepository)
    mock_asset_repo.get_asset_by_wallet_id_and_asset_id.return_value = (
        mock_asset,
        None,
    )

    mock_transaction_usecase = AsyncMock(spec=TransactionUsecase)
    mock_transaction_usecase.create_transaction.return_value = (None, None)

    mock_ledger_service = MagicMock()
    mock_ledger_service.transactions.record_transaction = AsyncMock(
        return_value=(None, None)
    )

    # Configure mock_config with NGN mapping to Nigeria
    mock_config.countries.countries = {
        "NG": MagicMock(name="Nigeria", currency="NGN", enabled=True)
    }
    mock_config.countries.countries["NG"].name = "Nigeria"
    mock_config.countries.countries["NG"].currency = "NGN"

    # Dependency overrides
    app.dependency_overrides[get_wallet_repository] = lambda: mock_wallet_repo
    app.dependency_overrides[get_asset_repository] = lambda: mock_asset_repo
    app.dependency_overrides[get_transaction_usecase] = lambda: mock_transaction_usecase
    app.dependency_overrides[get_ledger_service] = lambda: mock_ledger_service
    app.dependency_overrides[get_config] = lambda: mock_config

    payload = {
        "event": "deposit.success",
        "data": {
            "id": "tx_123",
            "reference": "ref_123",
            "senderAddress": "0x1234567890123456789012345678901234567890",
            "recipientAddress": "0x1234567890123456789012345678901234567890",
            "amount": "100.50",
            "amountPaid": "100.50",
            "currency": "ngn",
            "confirmations": 10,
            "confirmed": True,
            "hash": "0xhash123",
            "status": "SUCCESS",
            "type": "DEPOSIT",
            "network": "base",
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-01T00:00:00Z",
            "asset": {
                "id": str(mock_asset.asset_id),
                "address": "0x1234567890123456789012345678901234567890",
                "decimals": 18,
                "isActive": True,
                "logoUrl": "http://example.com/logo.png",
                "name": "USDC",
                "network": "base",
                "symbol": "USDC",
                "standard": "ERC20",
            },
            "blockchain": {
                "id": "chain_123",
                "createdAt": "2023-01-01T00:00:00Z",
                "derivationPath": "m/44/60/0/0/0",
                "isActive": True,
                "isEvmCompatible": True,
                "logoUrl": "http://example.com/logo.png",
                "name": "base",
                "slug": "base",
                "symbol": "ETH",
                "updatedAt": "2023-01-01T00:00:00Z",
                "network": "mainnet",
                "tokenStandard": None,
            },
            "wallet": {
                "id": "wallet_123",
                "address": "0x1234567890123456789012345678901234567890",
                "createdAt": "2023-01-01T00:00:00Z",
                "derivationPath": "m/44/60/0/0/0",
                "isActive": True,
                "name": "My Wallet",
                "network": "base",
                "updatedAt": "2023-01-01T00:00:00Z",
                "status": "active",
            },
            "amlScreening": {
                "status": "cleared",
                "message": "Cleared",
                "provider": "ComplyCube",
            },
        },
    }

    response = client.post("/api/v1/webhooks/blockrader", json=payload)

    assert response.status_code == 200
    assert response.json() == {"message": "Webhook received and processed"}

    # Verify that create_transaction was called with the correct country
    mock_transaction_usecase.create_transaction.assert_called_once()
    args, _ = mock_transaction_usecase.create_transaction.call_args
    params = args[0]
    assert params.country == "Nigeria"
    assert params.currency == "ngn"

    # Clean up
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_initiate_withdrawal_country_detection(
    mock_wallet, mock_asset, mock_config
):
    # This test verifies that initiate_withdrawal correctly sets the country based on currency
    from src.dtos.wallet_dtos import WithdrawalRequest
    from src.types.types import WithdrawalMethod
    from src.usecases.wallet_usecases import WalletManagerUsecase

    # Setup mocks
    mock_service = MagicMock()
    mock_service.config = mock_config
    mock_service.wallet_repository = AsyncMock()
    mock_service.wallet_repository.get_wallet_by_user_id.return_value = (
        mock_wallet,
        None,
    )
    mock_service.asset_repository = AsyncMock()
    mock_service.asset_repository.get_asset_by_wallet_id_and_asset_id.return_value = (
        mock_asset,
        None,
    )
    mock_service.transaction_usecase = AsyncMock()
    mock_service.transaction_usecase.update_transaction_status.return_value = None
    mock_service.transaction_usecase.update_transaction_fee.return_value = None
    mock_service.paycrest_service = MagicMock()
    mock_paycrest_response = MagicMock()
    mock_paycrest_response.data = Decimal("1")
    mock_service.paycrest_service.fetch_letest_usdc_rate = AsyncMock(
        return_value=(mock_paycrest_response, None)
    )

    mock_manager = MagicMock()
    mock_fee_response = MagicMock()
    mock_fee_response.data.networkFee = "10"
    mock_manager.withdraw_network_fee = AsyncMock(
        return_value=(mock_fee_response, None)
    )

    # Configure mock_config with NGN mapping to Nigeria
    mock_config.countries.countries = {
        "NG": MagicMock(name="Nigeria", currency="NGN", enabled=True)
    }
    mock_config.countries.countries["NG"].name = "Nigeria"
    mock_config.countries.countries["NG"].currency = "NGN"

    wallet_manager = WalletManagerUsecase(
        service=mock_service,
        manager=mock_manager,
        wallet_config=MagicMock(),
        ledger_config=MagicMock(),
    )

    user = User(id=mock_wallet.user_id, email="test@example.com")
    withdrawal_request = WithdrawalRequest(
        asset_id=str(mock_asset.asset_id),
        amount=Decimal("100"),
        narration="Test withdrawal",
        destination={
            "event": WithdrawalMethod.BANK_TRANSFER.value,
            "data": {
                "bank_code": "000",
                "account_number": "1234567890",
                "account_name": "Test User",
            },
        },
    )
    specific_withdrawal, _ = withdrawal_request.destination.to_specific_event()

    # Mock transaction to be returned
    mock_transaction = MagicMock()
    mock_transaction.id = "tx_123"

    # Create the async mock handler
    # IMPORTANT: The handler itself is an AsyncMock that returns the pair
    mock_handler = AsyncMock(return_value=(mock_transaction, None))

    # We patch get_handler to return our mock_handler
    # We patch where it is DEFINED to be safe, or where it is used.
    # Since it is a classmethod, patching the class in the module where it is used is good.
    with patch(
        "src.usecases.wallet_usecases.WithdrawalHandlerRegistry.get_handler",
        return_value=mock_handler,
    ) as mock_get_handler:
        await wallet_manager.initiate_withdrawal(
            user=user,
            withdrawal_request=withdrawal_request,
            specific_withdrawal=specific_withdrawal,
        )

        # Verify that the handler was called with create_transaction_params containing the correct country
        mock_handler.assert_called_once()
        _, kwargs = mock_handler.call_args
        params = kwargs["create_transaction_params"]
        assert params.country == "Nigeria"
        assert params.currency == "ngn"
