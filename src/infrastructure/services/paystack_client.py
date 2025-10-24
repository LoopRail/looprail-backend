from typing import Any, Optional, Tuple

from src.infrastructure.services.base_client import BaseClient
from src.infrastructure.settings import PaystackConfig
from src.types import Error, httpError
from src.types.paycrest_types import VerifyAccountResponse

BASE_URL = "https://api.paystack.co"


SUPPORTED_COUNTRIES = ["ng", "ky"]


class PaystackClient(BaseClient):
    """A base client for interacting with the Paystack API."""

    def __init__(self, config: PaystackConfig) -> None:
        """Initializes the Paystack client.

        Args:
            config: The Paystack configuration.
            path: The base path for the API endpoints.
        """
        self.config = config
        super().__init__("")

    def _get_base_url(self) -> str:
        return BASE_URL

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.paystack_api_key}",
            "Content-Type": "application/json",
        }


class PaystackService(PaystackClient):
    async def verify_account(
        self, account_number: str, institution_code: str, country: str
    ) -> Tuple[Optional[Any], Error]:
        """Verify bank account details"""

        if country.lower() not in SUPPORTED_COUNTRIES:
            return None, httpError(
                code=400,
                message=f"{country} not supported for paystack account verification",
            )

        data = {"bank_code": institution_code, "account_number": account_number}
        response, err = await self._get(
            VerifyAccountResponse, path_suffix="/bank/resolve", req_params=data
        )
        if err:
            return None, err
        return response, None
