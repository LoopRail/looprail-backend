"""
Test: 10 USDC bank withdrawal initiates a Paycrest payment order correctly.
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.types.paycrest import PaycrestPaymentOrder
from src.types.paycrest.types import PaycrestProviderAccount
from src.types.types import Currency, WithdrawalMethod, AssetType, TransactionStatus
from src.models.wallet_model import Wallet, Asset
from src.models.user_model import User
from src.types.common_types import Network
from src.usecases.wallet_usecases import WalletManagerUsecase


def _make_rate_resp(rate: str):
    quote = MagicMock()
    quote.rate = rate
    data = MagicMock()
    data.sell = quote
    resp = MagicMock()
    resp.data = data
    return resp


def _make_paycrest_order(payment_id: str, receive_address: str):
    provider_account = PaycrestProviderAccount(
        network="base",
        receiveAddress=receive_address,
        validUntil="2026-12-31T00:00:00Z",
    )
    order = PaycrestPaymentOrder(
        id=payment_id,
        amount="10",
        rate="1500",
        senderFee="0",
        transactionFee="0.01",
        reference="ref-test-001",
        providerAccount=provider_account,
    )
    resp = MagicMock()
    resp.data = order
    return resp


@pytest.mark.asyncio
async def test_bank_withdrawal_10_usdc_creates_paycrest_order():
    user_id = uuid4()
    wallet_id = uuid4()
    asset_id = uuid4()
    txn_id = uuid4()
    paycrest_id = "paycrest-order-abc123"
    receive_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    user_wallet_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"

    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        gender="male",
        ledger_identity_id="lid_123",
    )
    user_wallet = Wallet(
        id=wallet_id,
        user_id=user_id,
        address=user_wallet_address,
        chain="base",
        provider="blockrader",
        ledger_id="led_123",
    )
    asset = Asset(
        id=asset_id,
        wallet_id=wallet_id,
        address=user_wallet_address,
        symbol="USDC",
        precision=1000000,
        ledger_balance_id="bal_123",
        network=Network.MAINNET,
        name="USD Coin",
        asset_id=uuid4(),
        asset_type=AssetType.USDC,
        decimals=6,
    )

    # Mock transaction with bank_transfer relationship
    mock_bank_transfer = MagicMock()
    mock_bank_transfer.paycrest_txn_id = None
    mock_bank_transfer.paycrest_status = None

    mock_txn = MagicMock()
    mock_txn.id = txn_id
    mock_txn.reference = "ref-test-001"
    mock_txn.wallet_id = wallet_id
    mock_txn.bank_transfer = mock_bank_transfer

    # Build service mock
    mock_service = MagicMock()

    # Wallet / asset lookups
    mock_service.repo.get_wallet_by_user_id = AsyncMock(return_value=(user_wallet, None))
    mock_service._asset_repository.find_one = AsyncMock(return_value=(asset, None))

    # Sufficient balance
    mock_bal = MagicMock()
    mock_bal.balance = Decimal("100_000_000")  # 100 USDC in base units
    mock_bal.inflight_debit_balance = Decimal("0")
    mock_bal.queued_debit_balance = Decimal("0")
    mock_service.ledger_service.balances.get_balance = AsyncMock(return_value=(mock_bal, None))

    # Rate: not needed for USD withdrawal (amount is already USDC)
    mock_service.paycrest_service.fetch_letest_usdc_rate = AsyncMock(
        return_value=(_make_rate_resp("1500"), None)
    )

    # Paycrest order creation
    mock_service.paycrest_service.create_payment_order = AsyncMock(
        return_value=(_make_paycrest_order(paycrest_id, receive_address), None)
    )

    # Transaction creation + reload
    mock_service.transaction_usecase = MagicMock()
    mock_service.transaction_usecase.repo = MagicMock()
    mock_service.transaction_usecase.repo.create = AsyncMock(return_value=(mock_txn, None))
    mock_service.transaction_usecase.repo.find_one = AsyncMock(return_value=(mock_txn, None))
    mock_service.transaction_usecase.repo.update = AsyncMock(return_value=(mock_bank_transfer, None))
    mock_service.transaction_usecase.update_transaction_status = AsyncMock(return_value=None)
    mock_service.transaction_usecase.update_transaction_fee = AsyncMock(return_value=None)

    # Master wallet transfer (funds the Paycrest receive address)
    mock_master_wallet = MagicMock()
    mock_master_wallet.wallet_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    mock_master_asset = MagicMock()
    mock_master_asset.asset_id = "usdc-asset-id"
    mock_master_wallet.get = MagicMock(return_value=(mock_master_asset, None))
    mock_service.blockrader_config = MagicMock()
    mock_service.blockrader_config.wallets.get_wallet = MagicMock(
        return_value=(mock_master_wallet, None)
    )
    mock_service.wallet_manager = MagicMock()
    mock_service.wallet_manager.transfer = AsyncMock(return_value=(MagicMock(id="bk-tx-1"), None))

    # Country / bank resolution
    mock_service.config = MagicMock()
    mock_service.config.countries = MagicMock()
    mock_service.config.banks_data = MagicMock()

    mock_bank = MagicMock()
    mock_bank.code = "GTBINGLA"
    mock_service.config.banks_data.get = MagicMock(return_value=[mock_bank])

    mock_service.geolocation_service.get_location = AsyncMock(return_value=(None, None))

    # Ledger identity
    mock_service.ledger_service.identities = MagicMock()
    mock_service.ledger_service.identities.get_identity = AsyncMock(
        return_value=(MagicMock(identity_id="lid_123"), None)
    )

    usecase = WalletManagerUsecase(
        service=mock_service,
        manager=MagicMock(),
        wallet_config=MagicMock(),
        ledger_config=MagicMock(),
    )

    # Patch country lookup used inside the handler
    with patch(
        "src.usecases.wallet_usecases.get_country_code_by_currency",
        return_value="NG",
    ), patch(
        "src.usecases.wallet_usecases.get_country_name_by_currency",
        return_value="Nigeria",
    ), patch.object(
        usecase,
        "_transfer_from_master_wallet",
        new=AsyncMock(return_value=("bk-tx-1", None)),
    ):
        from src.dtos.wallet_dtos import WithdrawalRequest, GenericWithdrawalRequest, AuthorizationDetails

        withdrawal_req = WithdrawalRequest(
            asset_id=asset_id,
            amount=Decimal("10"),
            currency=Currency.US_Dollar,
            narration="Test withdrawal",
            destination=GenericWithdrawalRequest(
                event=WithdrawalMethod.BANK_TRANSFER,
                data={
                    "account_number": "1234567890",
                    "bank_code": "gtb",
                    "bank_name": "Guaranty Trust Bank",
                    "account_name": "John Doe",
                },
            ),
            authorization=AuthorizationDetails(
                authorization_method=1,
                pin="1234",
                ip_address="127.0.0.1",
            ),
        )

        err = await usecase._execute_bank_transfer_withdrawal(
            user=user,
            withdrawal_request=withdrawal_req,
            transaction=mock_txn,
        )

    assert err is None, f"Expected no error, got: {err}"

    # Paycrest order was created with 10 USDC
    mock_service.paycrest_service.create_payment_order.assert_called_once()
    call_kwargs = mock_service.paycrest_service.create_payment_order.call_args
    assert call_kwargs.kwargs["amount"] == Decimal("10")

    # paycrest_txn_id was stored on the bank transfer
    assert mock_bank_transfer.paycrest_txn_id == paycrest_id
