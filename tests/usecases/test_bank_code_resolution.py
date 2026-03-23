"""
Tests for the institution code resolution logic in
WalletManagerUsecase._execute_bank_transfer_withdrawal.

Verifies that:
- A valid bank ID is resolved to the correct SWIFT/institution code
- An unknown bank ID returns an error (no silent fallback)
- A missing country code returns an error
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.types.types import Bank, BanksData, Currency

# ─── Helpers ─────────────────────────────────────────────────────────────────


def make_banks_data(banks_by_country: dict) -> BanksData:
    """Build a BanksData instance from a plain dict of {country_code: [Bank, ...]}."""
    return BanksData(
        root={
            country: [Bank(**b) for b in bank_list]
            for country, bank_list in banks_by_country.items()
        }
    )


def make_withdrawal_request(
    currency=Currency.NAIRA,
    bank_code="070",
    account_number="0123456789",
    account_name="John Doe",
    bank_name="Fidelity Bank",
):
    req = MagicMock()
    req.currency = currency
    req.narration = "Test withdrawal"
    req.destination = MagicMock()
    req.destination.data = {
        "bank_code": bank_code,
        "bank_name": bank_name,
        "account_number": account_number,
        "account_name": account_name,
    }
    req.amount = Decimal("5000")
    return req


def make_transaction(network=None):
    from src.types.common_types import Network

    txn = MagicMock()
    txn.network = network or Network.MAINNET
    txn.id = "txn-123"
    txn.reference = "ref-abc"
    return txn


# ─── Tests ───────────────────────────────────────────────────────────────────


class TestInstitutionCodeResolution:
    """
    These tests directly exercise the institution-code lookup block
    inside _execute_bank_transfer_withdrawal by isolating its inputs
    (banks_data + country lookup) via mocks.
    """

    def _build_usecase(self, banks_data: BanksData, country_code: str | None):
        """
        Build a minimal WalletManagerUsecase with mocked service holding
        the given banks_data and a get_country_code_by_currency stub.
        """
        from src.usecases.wallet_usecases import WalletManagerUsecase

        service = MagicMock()
        service.config.banks_data = banks_data
        service.config.countries = MagicMock()

        # Stub _get_user_wallet and paycrest_service so test doesn't hit infra
        usecase = MagicMock(spec=WalletManagerUsecase)
        usecase.service = service
        usecase._get_user_wallet = AsyncMock(return_value=(MagicMock(), None))
        usecase._transfer_from_master_wallet = AsyncMock(return_value=("mw-tx-1", None))
        usecase.service.paycrest_service.create_payment_order = AsyncMock(
            return_value=(
                MagicMock(data=MagicMock(payment_id="p1", receive_address="0xABC")),
                None,
            )
        )
        usecase.service.transaction_usecase.update_transaction_status = AsyncMock(
            return_value=None
        )

        return usecase, country_code

    @pytest.mark.asyncio
    async def test_valid_bank_id_resolves_to_swift_code(self):
        """Happy path: numeric bank ID "070" maps to SWIFT code "FIDTNGLA"."""
        banks = make_banks_data(
            {"NG": [{"name": "Fidelity Bank", "id": "070", "code": "FIDTNGLA"}]}
        )
        usecase, country_code = self._build_usecase(banks, "NG")
        withdrawal_request = make_withdrawal_request(bank_code="070")
        transaction = make_transaction()

        with patch(
            "src.usecases.wallet_usecases.get_country_code_by_currency",
            return_value=country_code,
        ):
            # Call the real method bound to our mock instance
            from src.usecases.wallet_usecases import WalletManagerUsecase

            err = await WalletManagerUsecase._execute_bank_transfer_withdrawal(
                usecase,
                user=MagicMock(),
                withdrawal_request=withdrawal_request,
                transaction=transaction,
            )

        assert err is None
        call_args = usecase.service.paycrest_service.create_payment_order.call_args
        recipient = call_args.kwargs.get("recipient") or call_args.args[0]
        assert recipient.institution == "FIDTNGLA"

    @pytest.mark.asyncio
    async def test_unknown_bank_id_returns_error(self):
        """Unknown bank ID must return an error — no silent fallback."""
        banks = make_banks_data(
            {"NG": [{"name": "Fidelity Bank", "id": "070", "code": "FIDTNGLA"}]}
        )
        usecase, country_code = self._build_usecase(banks, "NG")
        withdrawal_request = make_withdrawal_request(bank_code="999")  # unknown
        transaction = make_transaction()

        with patch(
            "src.usecases.wallet_usecases.get_country_code_by_currency",
            return_value=country_code,
        ):
            from src.usecases.wallet_usecases import WalletManagerUsecase

            err = await WalletManagerUsecase._execute_bank_transfer_withdrawal(
                usecase,
                user=MagicMock(),
                withdrawal_request=withdrawal_request,
                transaction=transaction,
            )

        assert err is not None
        assert "999" in err.message
        # Paycrest must NOT have been called
        usecase.service.paycrest_service.create_payment_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_country_code_returns_error(self):
        """If currency has no matching country code, return an error immediately."""
        banks = make_banks_data(
            {"NG": [{"name": "Fidelity Bank", "id": "070", "code": "FIDTNGLA"}]}
        )
        usecase, _ = self._build_usecase(banks, country_code=None)  # no country
        withdrawal_request = make_withdrawal_request(bank_code="070")
        transaction = make_transaction()

        with patch(
            "src.usecases.wallet_usecases.get_country_code_by_currency",
            return_value=None,
        ):
            from src.usecases.wallet_usecases import WalletManagerUsecase

            err = await WalletManagerUsecase._execute_bank_transfer_withdrawal(
                usecase,
                user=MagicMock(),
                withdrawal_request=withdrawal_request,
                transaction=transaction,
            )

        assert err is not None
        assert "country code" in err.message.lower()
        usecase.service.paycrest_service.create_payment_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_bank_with_no_code_field_returns_error(self):
        """Bank entry exists by ID but has no `code` set — must return an error."""
        banks = make_banks_data(
            {"NG": [{"name": "Fidelity Bank", "id": "070", "code": None}]}
        )
        usecase, country_code = self._build_usecase(banks, "NG")
        withdrawal_request = make_withdrawal_request(bank_code="070")
        transaction = make_transaction()

        with patch(
            "src.usecases.wallet_usecases.get_country_code_by_currency",
            return_value=country_code,
        ):
            from src.usecases.wallet_usecases import WalletManagerUsecase

            err = await WalletManagerUsecase._execute_bank_transfer_withdrawal(
                usecase,
                user=MagicMock(),
                withdrawal_request=withdrawal_request,
                transaction=transaction,
            )

        assert err is not None
        usecase.service.paycrest_service.create_payment_order.assert_not_called()
