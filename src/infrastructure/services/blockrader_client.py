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
                                        WalletBalanceResponse,
                                        WithdrawalRequest, WithdrawalResponse)

T = TypeVar("T", bound=BaseModel)

BLOCKRADER_API_VERSION = "v1"
BASE_URL = f"https://api.blockradar.co/{BLOCKRADER_API_VERSION}"


class BlockRaderCLient:
    def __init__(self, config: BlockRaderConfig, path: str) -> None:
        self.config = config
        self._path = path

    def _get_url(self, path_suffix: str = "") -> str:
        return f"{BASE_URL}{self._path}{path_suffix}"

    async def _send(
        self,
        url: str,
        method: str,
        *,
        data: dict[str, any] = None,
        req_params: dict[str, any] = None,
    ) -> Response:
        headers = {"x-api-key": self.config.blockrader_api_key}
        async with AsyncClient() as client:
            res = await client.request(
                method, url, headers=headers, json=data, params=req_params
            )
            return res

    def _process_response(
        self, res: Response, response_model: Type[T]
    ) -> Tuple[Optional[T], Error]:
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
        url = self._get_url(path_suffix)
        res = await self._send(url, HTTPMethod.POST, data=data, req_params=req_params)
        return self._process_response(res, response_model)

    async def aml_lookup(
        self, req_params: AMLCheckRequest
    ) -> Tuple[Optional[AMLCheckResponse], Error]:
        return await self._get(
            AMLCheckResponse,
            path_suffix="/aml/lookup",
            req_params=req_params.model_dump(),
        )


class TransactionalMixin:
    async def get_details(self) -> Tuple[Optional[WalletAddressDetailResponse], Error]:
        return await self._get(WalletAddressDetailResponse)

    async def get_balance(
        self: "BlockRaderCLient", asset_id: str = None
    ) -> Tuple[Optional[WalletBalanceResponse], Error]:
        params = {"assetId": asset_id} if asset_id else None
        return await self._get(
            WalletBalanceResponse, path_suffix="/balance", req_params=params
        )

    async def get_balances(
        self: "BlockRaderCLient",
    ) -> Tuple[Optional[WalletBalanceResponse], Error]:
        return await self._get(WalletBalanceResponse, path_suffix="/balances")

    async def get_transactions(
        self: "BlockRaderCLient",
    ) -> Tuple[Optional[TransactionResponse], Error]:
        return await self._get(TransactionResponse, path_suffix="/transactions")

    async def get_transaction(
        self: "BlockRaderCLient", transaction_id: str
    ) -> Tuple[Optional[TransactionResponse], Error]:
        return await self._get(
            TransactionResponse, path_suffix=f"/transactions/{transaction_id}"
        )

    async def withdraw_network_fee(
        self: "BlockRaderCLient", request: NetworkFeeRequest
    ) -> Tuple[Optional[NetworkFeeResponse], Error]:
        return await self._post(
            NetworkFeeResponse,
            path_suffix="/withdraw/network-fee",
            data=request.model_dump(),
        )

    async def withdraw(
        self: "BlockRaderCLient", request: WithdrawalRequest
    ) -> Tuple[Optional[WithdrawalResponse], Error]:
        return await self._post(
            WithdrawalResponse,
            path_suffix="/withdraw",
            data=request.model_dump(),
        )


class AddressManager(BlockRaderCLient, TransactionalMixin):
    def __init__(
        self, config: BlockRaderConfig, wallet_id: str, address_id: str
    ) -> None:
        super().__init__(config, path=f"/wallets/{wallet_id}/addresses/{address_id}")


class WalletManager(BlockRaderCLient, TransactionalMixin):
    def __init__(self, config: BlockRaderConfig, wallet_id: str) -> None:
        self.wallet_id = wallet_id
        super().__init__(config, path=f"/wallets/{wallet_id}")

    def addresses(self, address_id: str) -> "AddressManager":
        return AddressManager(self.config, self.wallet_id, address_id)

    async def generate_address(
        self, request: CreateAddressRequest
    ) -> Tuple[Optional[WalletAddressDetailResponse], Error]:
        return await self._post(
            WalletAddressDetailResponse,
            path_suffix="/addresses",
            data=request.model_dump(),
        )
