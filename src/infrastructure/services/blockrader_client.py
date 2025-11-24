from typing import Any, Optional, Tuple, Type

from httpx import Response

from src.infrastructure.services.base_client import BaseClient, T
from src.infrastructure.settings import BlockRaderConfig
from src.types import Error, error
from src.types.blockrader import (AMLCheckRequest, AMLCheckResponse,
                                  CreateAddressRequest, NetworkFeeRequest,
                                  NetworkFeeResponse, TransactionResponse,
                                  WalletAddressDetailResponse,
                                  WalletBalanceResponse, WithdrawalRequest,
                                  WithdrawalResponse)

BLOCKRADER_API_VERSION = "v1"
BASE_URL = f"https://api.blockradar.co/{BLOCKRADER_API_VERSION}"


class BlockRaderCLient(BaseClient):
    """A base client for interacting with the BlockRadar API."""

    def __init__(self, config: BlockRaderConfig, path: str) -> None:
        """Initializes the BlockRader client.

        Args:
            config: The BlockRader configuration.
            path: The base path for the API endpoints.
        """
        self.config = config
        super().__init__(path)

    def _get_base_url(self) -> str:
        return BASE_URL

    def _get_headers(self) -> dict[str, str]:
        return {"x-api-key": self.config.blockrader_api_key}

    def _process_response(
        self, res: Response, response_model: Type[T]
    ) -> Tuple[Optional[T], Error]:
        """Processes the HTTP response from the BlockRadar API."""
        if res.status_code >= 500:
            return None, error(f"Service not available {res.status_code}")

        response_data = response_model.model_validate(res.json())

        if 300 <= response_data.statusCode < 500:
            return None, error(
                f"{response_data.message} status: {response_data.statusCode}"
            )

        return response_data, None

    async def aml_lookup(
        self, req_params: AMLCheckRequest
    ) -> Tuple[Optional[AMLCheckResponse], Error]:
        """Performs an AML (Anti-Money Laundering) lookup."""
        return await self._get(
            AMLCheckResponse,
            path_suffix="/aml/lookup",
            req_params=req_params.model_dump(),
        )


class TransactionalMixin:
    """A mixin for handling transactional endpoints of the BlockRadar API."""

    async def get_details(
        self: Any,
    ) -> Tuple[Optional[WalletAddressDetailResponse], Error]:
        """Retrieves details for a specific wallet address."""
        return await self._get(WalletAddressDetailResponse)

    async def get_balance(
        self: Any, asset_id: str = None
    ) -> Tuple[Optional[WalletBalanceResponse], Error]:
        """Retrieves the balance for a specific asset in a wallet."""
        params = {"assetId": asset_id} if asset_id else None
        return await self._get(
            WalletBalanceResponse, path_suffix="/balance", req_params=params
        )

    async def get_balances(
        self: Any,
    ) -> Tuple[Optional[WalletBalanceResponse], Error]:
        """Retrieves all asset balances in a wallet."""
        return await self._get(WalletBalanceResponse, path_suffix="/balances")

    async def get_transactions(
        self: Any,
    ) -> Tuple[Optional[TransactionResponse], Error]:
        """Retrieves a list of transactions for a wallet."""
        return await self._get(TransactionResponse, path_suffix="/transactions")

    async def get_transaction(
        self: Any, transaction_id: str
    ) -> Tuple[Optional[TransactionResponse], Error]:
        """Retrieves a specific transaction by its ID."""
        return await self._get(
            TransactionResponse, path_suffix=f"/transactions/{transaction_id}"
        )

    async def withdraw_network_fee(
        self: Any, request: NetworkFeeRequest
    ) -> Tuple[Optional[NetworkFeeResponse], Error]:
        """Calculates the network fee for a withdrawal."""
        return await self._post(
            NetworkFeeResponse,
            path_suffix="/withdraw/network-fee",
            data=request.model_dump(),
        )

    async def withdraw(
        self: Any, request: WithdrawalRequest
    ) -> Tuple[Optional[WithdrawalResponse], Error]:
        """Initiates a withdrawal from a wallet."""
        return await self._post(
            WithdrawalResponse,
            path_suffix="/withdraw",
            data=request.model_dump(),
        )


class AddressManager(BlockRaderCLient, TransactionalMixin):
    """Manages a specific address within a wallet."""

    def __init__(
        self, config: BlockRaderConfig, wallet_id: str, address_id: str
    ) -> None:
        """Initializes the AddressManager."""
        super().__init__(config, path=f"/wallets/{wallet_id}/addresses/{address_id}")


class WalletManager(BlockRaderCLient, TransactionalMixin):
    """Manages a specific wallet."""

    def __init__(self, config: BlockRaderConfig, wallet_id: str) -> None:
        """Initializes the WalletManager."""
        self.wallet_id = wallet_id
        super().__init__(config, path=f"/wallets/{wallet_id}")

    def addresses(self, address_id: str) -> "AddressManager":
        """Returns an AddressManager for a specific address within the wallet."""
        return AddressManager(self.config, self.wallet_id, address_id)

    async def generate_address(
        self, request: CreateAddressRequest
    ) -> Tuple[Optional[WalletAddressDetailResponse], Error]:
        """Generates a new address for the wallet."""
        return await self._post(
            WalletAddressDetailResponse,
            path_suffix="/addresses",
            data=request.model_dump(),
        )

    async def sign_transaction(self):
        return await self._post(any, path_suffix="contracts/write/sign")
