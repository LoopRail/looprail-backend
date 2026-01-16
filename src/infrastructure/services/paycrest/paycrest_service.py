from decimal import Decimal
from typing import  Optional, Tuple

from src.dtos import VerifyAccountResponse
from src.infrastructure.services.base_client import BaseClient
from src.infrastructure.settings import PayCrestConfig
from src.types import Chain, Error, error
from src.types.paycrest import (CreateOrderResponse, FetchLatestRatesResponse,
                                PaycrestRecipiant)
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)

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
        logger.debug("PaycrestClient initialized.")

    def _get_base_url(self) -> str:
        logger.debug("Getting Paycrest base URL: %s", BASE_URL)
        return BASE_URL

    def _get_headers(self) -> dict[str, str]:
        logger.debug("Getting Paycrest headers.")
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
        logger.debug("Creating payment order for amount %s, recipient %s, reference %s", amount, recipient, reference)
        rate, err = await self.fetch_letest_usdc_rate(amount, recipient.currency)
        if err:
            logger.error("Could not fetch rates for payment order: %s", err.message)
            return None, error("Could not fetch rates: Error: %s" % err.message)

        order_data = {
            "amount": float(amount),
            "token": "USDC",
            "network": Chain.BASE.value,
            "rate": rate.data,
            "recipient": recipient.model_dump(by_alias=True, exclude_none=True),
            "reference": reference,
            "returnAddress": return_address,
        }
        logger.debug("Sending payment order request with data: %s", order_data)
        response, err = await self._post(
            CreateOrderResponse, path_suffix="/sender/orders", data=order_data
        )
        if err:
            logger.error("Failed to create payment order: %s", err.message)
            return None, err
        logger.info("Payment order created successfully with ID: %s", response.order_id)
        return response, None

    async def verify_account(
        self, account_number: str, institution: str
    ) -> Tuple[Optional[VerifyAccountResponse], Error]:
        """Verify bank account details"""
        logger.debug("Verifying account for account number %s, institution %s", account_number, institution)
        data = {"institution": institution, "accountIdentifier": account_number}
        response, err = await self._post(
            VerifyAccountResponse, path_suffix="/verify-account", data=data
        )
        if err:
            logger.error("Failed to verify account for %s: %s", account_number, err.message)
            return None, err
        logger.info("Account %s verified successfully.", account_number)
        return response, None

    async def fetch_letest_usdc_rate(
        self, amount: float, currency: str
    ) -> Tuple[Optional[FetchLatestRatesResponse], Error]:
        """Verify bank account details"""
        logger.debug("Fetching latest USDC rate for amount %s %s", amount, currency)
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
            logger.error("Failed to fetch latest USDC rate for amount %s %s: %s", amount, currency, err.message)
            return None, err
        logger.info("Successfully fetched latest USDC rate: %s", response.data)
        return response, None
