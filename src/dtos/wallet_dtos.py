from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import UUID

from pydantic import field_serializer, field_validator

from src.dtos.base import Base
from src.types.common_types import Address, AssetId, Chain, WalletId
from src.types.error import Error, error
from src.types.types import Currency, WithdrawalMethod


class TransferType(Base):
    event: WithdrawalMethod
    data: Dict[str, Any]


class ExternalWalletTransferData(Base):
    address: Address
    chain: Chain


class BankTransferData(Base):
    bank_code: str
    account_number: str
    account_name: str

    @field_validator("account_number", mode="before")
    @classmethod
    def trim_account_number(cls, v: str) -> str:
        if not isinstance(v, str):
            raise error("account_number must be a string")
        v = v.strip()
        if not v.isdigit():
            raise error("account_number must contain only digits")
        if len(v) != 10:
            raise error("account_number must be exactly 10 digits long")
        return v


class BankTransferRequest(Base):
    event: WithdrawalMethod = WithdrawalMethod.BANK_TRANSFER
    data: BankTransferData


class ExtranalWalletTransferRequest(Base):
    event: WithdrawalMethod = WithdrawalMethod.EXTERNAL_WALLET
    data: ExternalWalletTransferData


class GenericWithdrawalRequest(Base):
    event: WithdrawalMethod
    data: Dict[str, Any]

    def to_specific_event(self) -> Tuple[Optional[TransferType], Error]:
        WITHDRAWAL_REQUEST_MAP: dict[str, Type[TransferType]] = {
            "withdraw:bank-transfer": BankTransferRequest,
            "withdraw:external-wallet": ExtranalWalletTransferRequest,
        }

        event_class = WITHDRAWAL_REQUEST_MAP.get(self.event)
        if event_class is None:
            return None, ValueError(f"{self.event} is not a supported event")
        return event_class(event=self.event, data=self.data), None


class AuthorizationDetails(Base):
    authorizationMethod: int
    localTime: int
    pin: str
    isWeb: bool
    amount: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    fingerprint: Optional[str] = None


class WithdrawalRequest(Base):
    asset_id: AssetId
    amount: Decimal
    currency: Currency
    narration: str
    destination: GenericWithdrawalRequest
    authorization: AuthorizationDetails


class AssetPublic(Base):
    id: AssetId
    name: str
    symbol: str
    decimals: int
    asset_type: str
    network: str
    address: str

    @field_serializer("id")
    def serialise_id(self, asset_id: UUID) -> AssetId:
        return AssetId.new(asset_id)


class WalletPublic(Base):
    id: WalletId
    address: str
    chain: str
    name: str | None = None
    assets: List[AssetPublic] = []

    @field_serializer("id")
    def serialise_id(self, wallet_id: UUID) -> WalletId:
        return WalletId.new(wallet_id)
