from decimal import Decimal
from typing import  Optional, Tuple

from src.dtos import VerifyAccountResponse
from src.infrastructure.services.base_client import BaseClient
from src.infrastructure.settings import PayCrestConfig
from src.types import Chain, Error, error
from src.types.paycrest import (CreateOrderResponse, FetchLatestRatesResponse,
                                PaycrestRecipiant)

PAYCREST_API_VERSION = "v1"
BASE_URL = f"https://api.paycrest.io/{PAYCREST_API_VERSION}"


class PaycrestClient(BaseClient):
    """A base client for interacting with the Paycrest API."""

    def __init__(self, config: PayCrestConfig) -> None:
        """Initializes the Paycrest client.

        Args:
            config: The Paycrest configuration.
            path: The base path for the API endpoints.
        """
        self.config = config
        super().__init__("")

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
        """Create a payment order to off-ramp tokens via Paycrest"""
        rate, err = await self.fetch_letest_usdc_rate(amount, recipient.currency)
        if err:
            return None, error(f"Could not fetch rates: Error: {err}")

        order_data = {
            "amount": float(amount),
            "token": "USDC",
            "network": Chain.BASE.value,
            "rate": rate.data,
            "recipient": recipient.model_dump(by_alias=True, exclude_none=True),
            "reference": reference,
            "returnAddress": return_address,
        }

        response, err = await self._post(
            CreateOrderResponse, path_suffix="/sender/orders", data=order_data
        )
        if err:
            return None, err
        return response, None

    async def verify_account(
        self, account_number: str, institution: str
    ) -> Tuple[Optional[VerifyAccountResponse], Error]:
        """Verify bank account details"""

        data = {"institution": institution, "accountIdentifier": account_number}
        response, err = await self._post(
            VerifyAccountResponse, path_suffix="/verify-account", data=data
        )
        if err:
            return None, err
        return response, None

    async def fetch_letest_usdc_rate(
        self, amount: float, currency: str
    ) -> Tuple[Optional[FetchLatestRatesResponse], Error]:
        """Verify bank account details"""

        data = {
            "token": "USDC",
            "amount": amount,
            "currency": currency,
        }
        response, err = await self._get(
            FetchLatestRatesResponse,
            path_suffix="/rates/{token}/{amount}/{currency}".format(**data),
            req_params={
                "network": Chain.BASE.value,
            },
        )
        if err:
            return None, err
        return response, None
