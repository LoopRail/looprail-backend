import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from uuid import uuid4

from src.usecases.wallet_usecases import WalletManagerUsecase
from src.dtos.wallet_dtos import WithdrawalRequest, AuthorizationDetails, GenericWithdrawalRequest, TransferType
from src.models.wallet_model import Wallet, Asset
from src.models.user_model import User
from src.types.types import Currency, WithdrawalMethod, AssetType, Network

@pytest.mark.asyncio
async def test_initiate_withdrawal_disallows_self_transfer():
    # Setup mocks
    mock_service = MagicMock()
    mock_manager = MagicMock()
    mock_wallet_config = MagicMock()
    mock_ledger_config = MagicMock()
    
    usecase = WalletManagerUsecase(
        service=mock_service,
        manager=mock_manager,
        wallet_config=mock_wallet_config,
        ledger_config=mock_ledger_config
    )

    valid_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    user_id = uuid4()
    user = User(id=user_id, email="test@example.com")
    user_wallet_id = uuid4()
    user_wallet = Wallet(id=user_wallet_id, user_id=user_id, address=valid_address, chain="ethereum", provider="blockrader", ledger_id="led_123")
    
    asset_id = uuid4()
    asset = Asset(
        id=asset_id, wallet_id=user_wallet_id, address=valid_address, symbol="USDC", precision=1000000, 
        ledger_balance_id="bal_123", network=Network.MAINNET, name="USD Coin", asset_id=uuid4(), asset_type=AssetType.USDC, decimals=6
    )

    withdrawal_request = WithdrawalRequest(
        asset_id=asset_id, amount=Decimal("100"), currency=Currency.US_Dollar, narration="Test",
        destination=GenericWithdrawalRequest(event=WithdrawalMethod.EXTERNAL_WALLET, data={"address": valid_address, "chain": "ethereum"}),
        authorization=AuthorizationDetails(authorization_method=1, pin="1234", ip_address="127.0.0.1")
    )
    
    specific_withdrawal = TransferType(event=WithdrawalMethod.EXTERNAL_WALLET, data={"address": valid_address, "chain": "ethereum"})

    mock_service.repo.get_wallet_by_user_id = AsyncMock(return_value=(user_wallet, None))
    mock_service._asset_repository.find_one = AsyncMock(return_value=(asset, None))
    
    # Mock balance response with all required fields
    mock_bal_resp = MagicMock()
    mock_bal_resp.balance = Decimal("1000000000")
    mock_bal_resp.inflight_debit_balance = Decimal("0")
    mock_bal_resp.queued_debit_balance = Decimal("0")
    mock_service.ledger_service.balances.get_balance = AsyncMock(return_value=(mock_bal_resp, None))
    
    mock_service.paycrest_service.fetch_letest_usdc_rate = AsyncMock(return_value=(MagicMock(data="1.0"), None))
    mock_service.config.withdrawal_fees = {"usd": 1.0}
    mock_service.geolocation_service.get_location = AsyncMock(return_value=(None, None))

    result, err = await usecase.initiate_withdrawal(user=user, withdrawal_request=withdrawal_request, specific_withdrawal=specific_withdrawal)

    assert result is None
    assert err is not None
    assert "Transfers to your own wallet address are not allowed" in err.message

@pytest.mark.asyncio
async def test_initiate_wallet_withdrawal_minimum_error_message():
    # Setup mocks
    mock_service = MagicMock()
    mock_manager = MagicMock()
    mock_wallet_config = MagicMock()
    mock_ledger_config = MagicMock()
    
    usecase = WalletManagerUsecase(
        service=mock_service,
        manager=mock_manager,
        wallet_config=mock_wallet_config,
        ledger_config=mock_ledger_config
    )

    valid_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    user_id = uuid4()
    user = User(id=user_id, email="test@example.com")
    user_wallet_id = uuid4()
    user_wallet = Wallet(id=user_wallet_id, user_id=user_id, address=valid_address, chain="ethereum", provider="blockrader", ledger_id="led_123")
    
    asset_id = uuid4()
    asset = Asset(
        id=asset_id, wallet_id=user_wallet_id, address="0x1234567890123456789012345678901234567890", symbol="USDC", precision=1000000, 
        ledger_balance_id="bal_123", network=Network.MAINNET, name="USD Coin", asset_id=uuid4(), asset_type=AssetType.USDC, decimals=6
    )

    # MIN_WALLET_TRANSFER_USD is 0.05.
    # Testing with NGN. Rate 1380.
    # 0.05 * 1380 = 69. Rounded up to nearest 10 is 70.
    withdrawal_request = WithdrawalRequest(
        asset_id=asset_id, amount=Decimal("10.0"), currency=Currency.NAIRA, narration="Test",
        destination=GenericWithdrawalRequest(event=WithdrawalMethod.EXTERNAL_WALLET, data={"address": "0x4567890123456789012345678901234567890123", "chain": "ethereum"}),
        authorization=AuthorizationDetails(authorization_method=1, pin="1234", ip_address="127.0.0.1")
    )
    
    specific_withdrawal = TransferType(event=WithdrawalMethod.EXTERNAL_WALLET, data={"address": "0x4567890123456789012345678901234567890123", "chain": "ethereum"})

    mock_service.repo.get_wallet_by_user_id = AsyncMock(return_value=(user_wallet, None))
    mock_service._asset_repository.find_one = AsyncMock(return_value=(asset, None))
    # Rate: 1380 NGN per 1 USD
    mock_service.paycrest_service.fetch_letest_usdc_rate = AsyncMock(return_value=(MagicMock(data="1380.0"), None))
    
    result, err = await usecase.initiate_withdrawal(user=user, withdrawal_request=withdrawal_request, specific_withdrawal=specific_withdrawal)

    assert result is None
    assert err is not None
    assert "Minimum wallet transfer is 70 NGN" in err.message

@pytest.mark.asyncio
async def test_initiate_bank_withdrawal_minimum_error_message():
    # Setup mocks
    mock_service = MagicMock()
    mock_manager = MagicMock()
    mock_wallet_config = MagicMock()
    mock_ledger_config = MagicMock()
    
    usecase = WalletManagerUsecase(
        service=mock_service,
        manager=mock_manager,
        wallet_config=mock_wallet_config,
        ledger_config=mock_ledger_config
    )

    valid_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    user_id = uuid4()
    user = User(id=user_id, email="test@example.com")
    user_wallet_id = uuid4()
    user_wallet = Wallet(id=user_wallet_id, user_id=user_id, address=valid_address, chain="ethereum", provider="blockrader", ledger_id="led_123")
    
    asset_id = uuid4()
    asset = Asset(
        id=asset_id, wallet_id=user_wallet_id, address="0x1234567890123456789012345678901234567890", symbol="USDC", precision=1000000, 
        ledger_balance_id="bal_123", network=Network.MAINNET, name="USD Coin", asset_id=uuid4(), asset_type=AssetType.USDC, decimals=6
    )

    # MIN_BANK_TRANSFER_NGN is 1.
    # We want min_bank_usd to be something like 0.1.
    # 1 / 0.1 = 10. Rate = 10.
    withdrawal_request = WithdrawalRequest(
        asset_id=asset_id, amount=Decimal("0.05"), currency=Currency.US_Dollar, narration="Test",
        destination=GenericWithdrawalRequest(event=WithdrawalMethod.BANK_TRANSFER, data={"account_number": "1234567890", "bank_code": "044"}),
        authorization=AuthorizationDetails(authorization_method=1, pin="1234", ip_address="127.0.0.1")
    )
    
    specific_withdrawal = TransferType(event=WithdrawalMethod.BANK_TRANSFER, data={"account_number": "1234567890", "bank_code": "044"})

    mock_service.repo.get_wallet_by_user_id = AsyncMock(return_value=(user_wallet, None))
    mock_service._asset_repository.find_one = AsyncMock(return_value=(asset, None))
    # Rate: 10 NGN per 1 USD
    mock_service.paycrest_service.fetch_letest_usdc_rate = AsyncMock(return_value=(MagicMock(data="10.0"), None))
    # Mock balance response
    mock_bal_resp = MagicMock()
    mock_bal_resp.balance = Decimal("1000")
    mock_bal_resp.inflight_debit_balance = Decimal("0")
    mock_bal_resp.queued_debit_balance = Decimal("0")
    mock_service.ledger_service.balances.get_balance = AsyncMock(return_value=(mock_bal_resp, None))
    
    result, err = await usecase.initiate_withdrawal(user=user, withdrawal_request=withdrawal_request, specific_withdrawal=specific_withdrawal)

    assert result is None
    assert err is not None
    # 1 / 10 = 0.10 USD.
    assert "Minimum bank transfer is 0.10 USD" in err.message
