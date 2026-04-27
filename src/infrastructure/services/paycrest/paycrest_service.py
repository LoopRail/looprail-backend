from decimal import Decimal
from typing import Optional, Tuple

from src.dtos import VerifyAccountResponse
from src.infrastructure.logger import get_logger
from src.infrastructure.services.base_client import BaseClient
from src.infrastructure.settings import PayCrestConfig
from src.types import Chain, Error, error
from src.types.paycrest import (
    CreateOrderResponse,
    FetchLatestRatesResponse,
    PaycrestRecipiant,
)

logger = get_logger(__name__)

BASE_URL = "https://api.paycrest.io/v2"


class PaycrestClient(BaseClient):
    """A base client for interacting with the Paycrest API."""

    def __init__(self, config: PayCrestConfig) -> None:
        self.config = config
        super().__init__("")
        logger.debug("PaycrestClient initialized.")

    def _get_base_url(self) -> str:
        return BASE_URL

    def _get_headers(self) -> dict[str, str]:
        return {
            "API-Key": self.config.paycrest_api_key,
            "Content-Type": "application/json",
        }


class PaycrestService(PaycrestClient):
    async def create_payment_order(
        self,
        amount: Decimal,
        recipient: PaycrestRecipiant,
        reference: str,
        return_address: str,
    ) -> Tuple[Optional[CreateOrderResponse], Error]:
        """Create a payment order to off-ramp tokens via Paycrest (v2)."""
        logger.debug(
            "Creating payment order for amount %s, recipient %s, reference %s",
            amount,
            recipient,
            reference,
        )
        order_data = {
            "amount": str(amount),
            "source": {
                "type": "crypto",
                "currency": "USDC",
                "network": Chain.BASE.value,
                "refundAddress": return_address,
            },
            "destination": {
                "type": "fiat",
                "currency": recipient.currency.upper(),
                "recipient": recipient.model_dump(
                    by_alias=True,
                    exclude={"currency_enum", "metadata"},
                    exclude_none=True,
                ),
            },
            "reference": reference,
        }
        logger.debug("Sending payment order request with data: %s", order_data)
        response, err = await self._post(
            CreateOrderResponse, path_suffix="/sender/orders", data=order_data
        )
        if err:
            logger.error("Failed to create payment order: %s", err.message)
            return None, err
        logger.info(
            "Payment order created successfully with ID: %s", response.data.payment_id
        )
        return response, None

    async def verify_account(
        self, account_number: str, institution: str
    ) -> Tuple[Optional[VerifyAccountResponse], Error]:
        """Verify bank account details."""
        logger.debug(
            "Verifying account for account number %s, institution %s",
            account_number,
            institution,
        )
        data = {"institution": institution, "accountIdentifier": account_number}
        response, err = await self._post(
            VerifyAccountResponse, path_suffix="/verify-account", data=data
        )
        if err:
            logger.error(
                "Failed to verify account for %s: %s", account_number, err.message
            )
            return None, err
        logger.info("Account %s verified successfully.", account_number)
        return response, None

    async def fetch_letest_usdc_rate(
        self, amount: float, currency: str
    ) -> Tuple[Optional[FetchLatestRatesResponse], Error]:
        """Fetch buy/sell rate quotes for USDC on Base (v2).
        Amount must be in USDC — capped at 1000 per API requirements.
        """
        usdc_amount = min(1000.0, max(1.0, amount))
        logger.debug("Fetching latest USDC rate for amount %s %s", usdc_amount, currency)
        path = f"/rates/{Chain.BASE.value}/USDC/{usdc_amount}/{currency.upper()}"
        response, err = await self._get(
            FetchLatestRatesResponse,
            path_suffix=path,
            req_params={"side": "sell"},
        )
        if err:
            logger.error(
                "Failed to fetch latest USDC rate for amount %s %s: %s",
                usdc_amount,
                currency,
                err.message,
            )
            return None, err
        logger.info("Successfully fetched latest USDC rate: %s", response.data)
        return response, None
