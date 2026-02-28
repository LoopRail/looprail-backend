import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from uuid import uuid4
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
)
from src.api.dependencies.services import get_ledger_service
from src.infrastructure.repositories import (
    AssetRepository,
    WalletRepository,
    SessionRepository,
    UserRepository,
)
from src.main import app
from src.models import Asset, User, Wallet
from src.types.country_types import CountryInfo
from src.types.types import AssetType, WithdrawalMethod
from src.usecases import TransactionUsecase
from src.usecases.wallet_usecases import WalletManagerUsecase
from src.dtos.wallet_dtos import WithdrawalRequest
from src.types import TransactionType, TransactionStatus

@pytest.fixture
def client():
    # Setup app state essentials for tests to handle direct state access if any
    app.state.rq_manager = MagicMock()
    app.state.resend = MagicMock()
    return TestClient(app)

@pytest.fixture
def mock_wallet():
    return Wallet(
        id=uuid4(),
        user_id=uuid4(),
        address="0x1234567890123456789012345678901234567890",
        is_active=True,
    )

@pytest.fixture
def mock_asset(mock_wallet):
    return Asset(
        id=uuid4(),
        wallet_id=mock_wallet.id,
        ledger_balance_id="bal_123",
        asset_id=uuid4(),
        symbol="USDC",
        is_active=True,
    )

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.countries = MagicMock()
    config.countries.countries = {}
    config.app.logo_url = "http://example.com/logo.png"
    
    mock_bank = MagicMock()
    mock_bank.name = "Test Bank"
    config.banks_data = MagicMock()
    config.banks_data.get.return_value = [mock_bank]
    
    return config

@pytest.mark.asyncio
async def test_webhook_deposit_success_country_detection(
    client, mock_wallet, mock_asset, mock_config
):
    # Setup mocks
    mock_source_asset = MagicMock()
    mock_source_asset.asset_id = "56204320-5cb3-4850-8353-feff91c59498"
    mock_source_asset.name = "USDC"
    mock_source_wallet = MagicMock()
    mock_source_wallet.wallet_name = "My Wallet"
    mock_source_wallet.get.return_value = (mock_source_asset, None)
    mock_config.block_rader.wallets.get_wallet.return_value = (
        mock_source_wallet,
        None,
    )

    mock_asset_repo = AsyncMock()
    mock_asset_repo.find_one.return_value = (
        mock_asset,
        None,
    )
    mock_wallet_repo = AsyncMock()
    mock_wallet_repo.get_wallet_by_address.return_value = (
        mock_wallet,
        None,
    )
    
    # Required for notification sub-flow
    mock_session_repo = AsyncMock()
    mock_session_repo.get_user_sessions.return_value = []
    
    mock_notification_usecase = MagicMock()
    mock_user_repo = AsyncMock()
    mock_resend_service = MagicMock()

    mock_txn = MagicMock()
    mock_txn.id = "tx_123"
    mock_txn.reference = "ref_123"
    
    mock_transaction_usecase = AsyncMock()
    mock_transaction_usecase.repo = AsyncMock()
    mock_transaction_usecase.repo.find_one.return_value = (None, None)
    mock_transaction_usecase.repo.update.return_value = (mock_txn, None)
    mock_transaction_usecase.create_transaction.return_value = (mock_txn, None)

    mock_ledger_service = MagicMock()
    mock_ledger_service.transactions = MagicMock()
    mock_ledger_service.transactions.record_transaction = AsyncMock(
        return_value=(MagicMock(transaction_id="ledger_tx_123"), None)
    )
    mock_ledger_service.balances = MagicMock()
    bal_mock = MagicMock()
    bal_mock.balance = Decimal("1000000")
    bal_mock.inflight_debit_balance = Decimal("0")
    bal_mock.queued_debit_balance = Decimal("0")
    mock_ledger_service.balances.get_balance = AsyncMock(
        return_value=(bal_mock, None)
    )

    mock_lock_service = MagicMock()
    mock_lock_service.get.return_value.acquire = AsyncMock(
        return_value=(uuid4(), None)
    )
    mock_lock_service.get.return_value.release = AsyncMock(
        return_value=None
    )

    # Configure mock_config with NGN mapping to Nigeria
    mock_config.countries.countries = {
        "NG": CountryInfo(
            name="Nigeria",
            iso2="NG",
            iso3="NGA",
            dial_code="+234",
            currency="NGN",
            enabled=True,
        )
    }

    # Dependency overrides
    app.dependency_overrides[get_wallet_repository] = lambda: mock_wallet_repo
    app.dependency_overrides[get_asset_repository] = lambda: mock_asset_repo
    app.dependency_overrides[get_transaction_usecase] = lambda: mock_transaction_usecase
    app.dependency_overrides[get_ledger_service] = lambda: mock_ledger_service
    app.dependency_overrides[get_config] = lambda: mock_config
    app.dependency_overrides[get_verify_webhook_request] = lambda: AsyncMock()
    app.dependency_overrides[get_lock_service] = lambda: mock_lock_service
    app.dependency_overrides[get_session_repository] = lambda: mock_session_repo
    app.dependency_overrides[get_notification_usecase] = lambda: mock_notification_usecase
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    app.dependency_overrides[get_resend_service] = lambda: mock_resend_service

    now = datetime.now(timezone.utc)
    
    payload = {
        "event": "deposit.success",
        "data": {
            "id": "evt_123",
            "reference": "ref_123",
            "status": "SUCCESS",
            "type": "DEPOSIT",
            "network": "mainnet",
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
            "amount": "100.00",
            "amountPaid": "100.00",
            "currency": "NGN",
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
                "id": "56204320-5cb3-4850-8353-feff91c59498",
                "name": "USDC",
                "symbol": "USDC",
                "network": "mainnet",
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
                "network": "mainnet",
                "isActive": True,
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
                "derivationPath": "m/44/60/0/0/0"
            }
        },
    }

    response = client.post("/api/v1/webhooks/blockrader", json=payload)

    if response.status_code != 200:
        print(f"Response Detail: {response.text}")

    assert response.status_code == 200
    # Verify that create_transaction was called with the correct country name
    mock_transaction_usecase.create_transaction.assert_called_once()
    params = mock_transaction_usecase.create_transaction.call_args[0][0]
    assert params.country == "Nigeria"

    # Clean up overrides
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_initiate_withdrawal_country_detection(
    mock_wallet, mock_asset, mock_config
):
    # Setup mocks
    mock_service = MagicMock()
    mock_service.repo = AsyncMock()
    mock_service.repo.get_wallet_by_user_id.return_value = (
        mock_wallet,
        None,
    )
    mock_service.wallet_repository = mock_service.repo
    mock_service._asset_repository = AsyncMock()
    mock_service._asset_repository.find_one.return_value = (
        mock_asset,
        None,
    )
    
    mock_txn = MagicMock()
    mock_txn.id = "tx_123"
    mock_txn.reference = "ref_123"
    
    mock_service.transaction_usecase = AsyncMock()
    mock_service.transaction_usecase.repo = AsyncMock()
    mock_service.transaction_usecase.repo.update.return_value = (mock_txn, None)
    mock_service.transaction_usecase.update_transaction_status.return_value = None
    mock_service.transaction_usecase.update_transaction_fee.return_value = None
    
    mock_service.paycrest_service = MagicMock()
    mock_paycrest_response = MagicMock()
    mock_paycrest_response.data = Decimal("1500")
    mock_service.paycrest_service.fetch_letest_usdc_rate = AsyncMock(
        return_value=(mock_paycrest_response, None)
    )
    
    mock_ledger_service = MagicMock()
    mock_ledger_service.transactions = MagicMock()
    mock_ledger_service.transactions.record_transaction = AsyncMock(
        return_value=(MagicMock(transaction_id="ledger_tx_123"), None)
    )
    mock_ledger_service.balances = MagicMock()
    bal_mock = MagicMock()
    bal_mock.balance = Decimal("1000000")
    bal_mock.inflight_debit_balance = Decimal("0")
    bal_mock.queued_debit_balance = Decimal("0")
    mock_ledger_service.balances.get_balance = AsyncMock(
        return_value=(bal_mock, None)
    )
    mock_service.ledger_service = mock_ledger_service
    mock_service.config = mock_config

    mock_manager = MagicMock()
    mock_fee_response = MagicMock()
    mock_fee_response.data.networkFee = "10"
    mock_manager.withdraw_network_fee = AsyncMock(
        return_value=(mock_fee_response, None)
    )

    # Configure mock_config with NGN mapping to Nigeria
    mock_config.countries.countries = {
        "NG": CountryInfo(
            name="Nigeria",
            iso2="NG",
            iso3="NGA",
            dial_code="+234",
            currency="NGN",
            enabled=True,
        )
    }

    mock_blockrader_asset = MagicMock()
    mock_blockrader_asset.blockrader_asset_id = "br_asset_123"
    mock_wallet_config = MagicMock()
    mock_wallet_config.get.return_value = (mock_blockrader_asset, None)
    mock_ledger_config = MagicMock()

    wallet_manager = WalletManagerUsecase(
        service=mock_service,
        manager=mock_manager,
        wallet_config=mock_wallet_config,
        ledger_config=mock_ledger_config,
    )

    user = User(id=mock_wallet.user_id, email="test@example.com")
    withdrawal_request = WithdrawalRequest(
        asset_id=f"ast_{mock_asset.asset_id}",
        amount=Decimal("100"),
        currency="ngn",
        narration="Test withdrawal",
        destination={
            "event": WithdrawalMethod.BANK_TRANSFER.value,
            "data": {
                "bank_code": "000",
                "bank_name": "Test Bank",
                "account_number": "1234567890",
                "account_name": "Test User",
            },
        },
        authorization={
            "authorization_method": 1,
            "pin": "1234",
        },
    )
    specific_withdrawal, _ = withdrawal_request.destination.to_specific_event()

    # Create the async mock handler
    mock_handler = AsyncMock(return_value=(mock_txn, None))

    # We patch get_handler to return our mock_handler
    with patch(
        "src.usecases.wallet_usecases.WithdrawalHandlerRegistry.get_handler",
        return_value=mock_handler,
    ) as mock_get_handler:
        await wallet_manager.initiate_withdrawal(
            user=user,
            withdrawal_request=withdrawal_request,
            specific_withdrawal=specific_withdrawal,
        )

        # Verify that the handler was called with create_transaction_params containing the correct country name
        mock_handler.assert_called_once()
        _, kwargs = mock_handler.call_args
        params = kwargs["create_transaction_params"]
        assert params.country == "Nigeria"
