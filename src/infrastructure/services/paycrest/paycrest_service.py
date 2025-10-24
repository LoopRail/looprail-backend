from decimal import Decimal
from typing import Any, Optional, Tuple

from pydantic import BaseModel

from src.dtos import OrderResponse
from src.infrastructure.services.base_client import BaseClient
from src.infrastructure.settings import PayCrestConfig
from src.types import Error, error
from src.types.paycrest_types import VerifyAccountResponse

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
        user_id: int,
        token: str,
        amount: Decimal,
        network: str,
        recipient: dict,
        reference: str,
        return_address: str,
    ) -> Tuple[Optional[OrderResponse], Error]:
        """Create a payment order to off-ramp tokens via Paycrest"""

        currency = recipient.get("currency")
        if not currency:
            return None, error("Recipient dict must contain a 'currency' key")

        rate, err = await self.fetch_rate(token, amount, currency, network)
        if err:
            return None, err

        order_data = {
            "amount": float(amount),
            "token": token,
            "network": network,
            "rate": rate,
            "recipient": recipient,
            "reference": reference,
            "returnAddress": return_address,
        }

        response, err = await self._post(
            OrderResponse, path_suffix="/sender/orders", data=order_data
        )
        if err:
            return None, err

        if response:
            response.user_id = user_id

        return response, None

    async def verify_account(
        self, account_number: str, institution: str
    ) -> Tuple[Optional[Any], Error]:
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
    ) -> Tuple[Optional[VerifyAccountResponse], Error]:
        """Verify bank account details"""

        data = {
            "token": "USDC",
            "amount": amount,
            "currency": currency,
        }
        response, err = await self._get(
            VerifyAccountResponse,
            path_suffix="/rates/{token}/{amount}/{currency}".format(**data),
            req_params={
                "network": "base",
            },
        )
        if err:
            return None, err
        return response, None
