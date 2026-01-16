from typing import Any, Optional, Tuple

from src.dtos import VerifyAccountResponse
from src.infrastructure.services.base_client import BaseClient
from src.infrastructure.settings import PaystackConfig
from src.types import Error, httpError
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)

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
        logger.debug("PaystackClient initialized.")

    def _get_base_url(self) -> str:
        logger.debug("Getting Paystack base URL: %s", BASE_URL)
        return BASE_URL

    def _get_headers(self) -> dict[str, str]:
        logger.debug("Getting Paystack headers with authorization.")
        return {
            "Authorization": f"Bearer {self.config.paystack_api_key}",
            "Content-Type": "application/json",
        }


class PaystackService(PaystackClient):
    async def verify_account(
        self, account_number: str, institution_code: str, country: str
    ) -> Tuple[Optional[Any], Error]:
        """Verify bank account details"""
        logger.debug("Verifying account for account number %s, institution code %s, country %s", account_number, institution_code, country)
        if country.lower() not in SUPPORTED_COUNTRIES:
            logger.error("Country %s not supported for Paystack account verification.", country)
            return None, httpError(
                code=400,
                message="%s not supported for paystack account verification" % country,
            )

        data = {"bank_code": institution_code, "account_number": account_number}
        response, err = await self._get(
            VerifyAccountResponse, path_suffix="/bank/resolve", req_params=data
        )
        if err:
            logger.error("Failed to verify account for %s: %s", account_number, err.message)
            return None, err
        logger.info("Account %s verified successfully.", account_number)
        return response, None
