from typing import Optional, Tuple, Type, TypeVar

from httpx import AsyncClient, Response
from pydantic import BaseModel

from src.infrastructure.settings import BlockRaderConfig
from src.types import Error, HTTPMethod, error
from src.types.blockrader_types import (AMLCheckRequest, AMLCheckResponse,
                                        CreateAddressRequest,
                                        NetworkFeeRequest, NetworkFeeResponse,
                                        TransactionResponse,
                                        WalletAddressDetailResponse,
                                        WalletAddressResponse,
                                        WalletBalanceResponse,
                                        WalletDetailsResponse,
                                        WithdrawalRequest, WithdrawalResponse)

T = TypeVar("T", bound=BaseModel)

BLOCKRADER_API_VERSION = "v1"
BASE_URL = f"https://api.blockradar.co/{BLOCKRADER_API_VERSION}"


class BlockRaderCLient:
    """A base client for interacting with the BlockRadar API."""
    def __init__(self, config: BlockRaderConfig, path: str) -> None:
        """Initializes the BlockRader client.

        Args:
            config: The BlockRader configuration.
            path: The base path for the API endpoints.
        """
        self.config = config
        self._path = path

    def _get_url(self, path_suffix: str = "") -> str:
        """Constructs the full URL for an API endpoint.

        Args:
            path_suffix: The suffix to append to the base path.

        Returns:
            The full URL.
        """
        return f"{BASE_URL}{self._path}{path_suffix}"

    async def _send(
        self,
        url: str,
        method: str,
        *,
        data: dict[str, any] = None,
        req_params: dict[str, any] = None,
    ) -> Response:
        """Sends an HTTP request to the BlockRadar API.

        Args:
            url: The URL to send the request to.
            method: The HTTP method to use.
            data: The data to send with the request.
            req_params: The request parameters.

        Returns:
            The HTTP response.
        """
        headers = {"x-api-key": self.config.blockrader_api_key}
        async with AsyncClient() as client:
            res = await client.request(
                method, url, headers=headers, json=data, params=req_params
            )
            return res

    def _process_response(
        self, res: Response, response_model: Type[T]
    ) -> Tuple[Optional[T], Error]:
        """Processes the HTTP response from the BlockRadar API.

        Args:
            res: The HTTP response.
            response_model: The Pydantic model to validate the response against.

        Returns:
            A tuple containing the response data and an error, if any.
        """
        if res.status_code >= 500:
            return None, error(f"Service not available {res.status_code}")

        response_data = response_model.model_validate(res.json())

        if 300 <= response_data.statusCode < 500:
            return None, error(
                f"{response_data.message} status: {response_data.statusCode}"
            )

        return response_data, None

    async def _get(
        self,
        response_model: Type[T],
        path_suffix: str = "",
        req_params: dict[str, any] = None,
    ) -> Tuple[Optional[T], Error]:
        """Sends a GET request to the BlockRadar API.

        Args:
            response_model: The Pydantic model to validate the response against.
            path_suffix: The suffix to append to the base path.
            req_params: The request parameters.

        Returns:
            A tuple containing the response data and an error, if any.
        """
        url = self._get_url(path_suffix)
        res = await self._send(url, HTTPMethod.GET, req_params=req_params)
        return self._process_response(res, response_model)

    async def _post(
        self,
        response_model: Type[T],
        path_suffix: str = "",
        data: dict[str, any] = None,
        req_params: dict[str, any] = None,
    ) -> Tuple[Optional[T], Error]:
        """Sends a POST request to the BlockRadar API.

        Args:
            response_model: The Pydantic model to validate the response against.
            path_suffix: The suffix to append to the base path.
            data: The data to send with the request.
            req_params: The request parameters.

        Returns:
            A tuple containing the response data and an error, if any.
        """
        url = self._get_url(path_suffix)
        res = await self._send(url, HTTPMethod.POST, data=data, req_params=req_params)
        return self._process_response(res, response_model)

    async def aml_lookup(
        self, req_params: AMLCheckRequest
    ) -> Tuple[Optional[AMLCheckResponse], Error]:
        """Performs an AML (Anti-Money Laundering) lookup.

        Args:
            req_params: The request parameters for the AML lookup.

        Returns:
            A tuple containing the AML check response and an error, if any.
        """
        return await self._get(
            AMLCheckResponse,
            path_suffix="/aml/lookup",
            req_params=req_params.model_dump(),
        )


class TransactionalMixin:
    """A mixin for handling transactional endpoints of the BlockRadar API."""
    async def get_details(self) -> Tuple[Optional[WalletAddressDetailResponse], Error]:
        """Retrieves details for a specific wallet address.

        Returns:
            A tuple containing the wallet address details and an error, if any.
        """
        return await self._get(WalletAddressDetailResponse)

    async def get_balance(
        self: "BlockRaderCLient", asset_id: str = None
    ) -> Tuple[Optional[WalletBalanceResponse], Error]:
        """Retrieves the balance for a specific asset in a wallet.

        Args:
            asset_id: The ID of the asset to retrieve the balance for.

        Returns:
            A tuple containing the wallet balance and an error, if any.
        """
        params = {"assetId": asset_id} if asset_id else None
        return await self._get(
            WalletBalanceResponse, path_suffix="/balance", req_params=params
        )

    async def get_balances(
        self: "BlockRaderCLient",
    ) -> Tuple[Optional[WalletBalanceResponse], Error]:
        """Retrieves all asset balances in a wallet.

        Returns:
            A tuple containing the wallet balances and an error, if any.
        """
        return await self._get(WalletBalanceResponse, path_suffix="/balances")

    async def get_transactions(
        self: "BlockRaderCLient",
    ) -> Tuple[Optional[TransactionResponse], Error]:
        """Retrieves a list of transactions for a wallet.

        Returns:
            A tuple containing the list of transactions and an error, if any.
        """
        return await self._get(TransactionResponse, path_suffix="/transactions")

    async def get_transaction(
        self: "BlockRaderCLient", transaction_id: str
    ) -> Tuple[Optional[TransactionResponse], Error]:
        """Retrieves a specific transaction by its ID.

        Args:
            transaction_id: The ID of the transaction to retrieve.

        Returns:
            A tuple containing the transaction and an error, if any.
        """
        return await self._get(
            TransactionResponse, path_suffix=f"/transactions/{transaction_id}"
        )

    async def withdraw_network_fee(
        self: "BlockRaderCLient", request: NetworkFeeRequest
    ) -> Tuple[Optional[NetworkFeeResponse], Error]:
        """Calculates the network fee for a withdrawal.

        Args:
            request: The request parameters for the network fee calculation.

        Returns:
            A tuple containing the network fee and an error, if any.
        """
        return await self._post(
            NetworkFeeResponse,
            path_suffix="/withdraw/network-fee",
            data=request.model_dump(),
        )

    async def withdraw(
        self: "BlockRaderCLient", request: WithdrawalRequest
    ) -> Tuple[Optional[WithdrawalResponse], Error]:
        """Initiates a withdrawal from a wallet.

        Args:
            request: The request parameters for the withdrawal.

        Returns:
            A tuple containing the withdrawal response and an error, if any.
        """
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
        """Initializes the AddressManager.

        Args:
            config: The BlockRader configuration.
            wallet_id: The ID of the wallet.
            address_id: The ID of the address.
        """
        super().__init__(config, path=f"/wallets/{wallet_id}/addresses/{address_id}")


class WalletManager(BlockRaderCLient, TransactionalMixin):
    """Manages a specific wallet."""
    def __init__(self, config: BlockRaderConfig, wallet_id: str) -> None:
        """Initializes the WalletManager.

        Args:
            config: The BlockRader configuration.
            wallet_id: The ID of the wallet.
        """
        self.wallet_id = wallet_id
        super().__init__(config, path=f"/wallets/{wallet_id}")

    def addresses(self, address_id: str) -> "AddressManager":
        """Returns an AddressManager for a specific address within the wallet.

        Args:
            address_id: The ID of the address.

        Returns:
            An AddressManager instance.
        """
        return AddressManager(self.config, self.wallet_id, address_id)

    async def generate_address(
        self, request: CreateAddressRequest
    ) -> Tuple[Optional[WalletAddressDetailResponse], Error]:
        """Generates a new address for the wallet.

        Args:
            request: The request parameters for generating the address.

        Returns:
            A tuple containing the new address details and an error, if any.
        """
        return await self._post(
            WalletAddressDetailResponse,
            path_suffix="/addresses",
            data=request.model_dump(),
        )
