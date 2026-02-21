from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import Field, field_validator

from src.dtos.base import Base
from src.types.common_types import Address, AssetId, Chain, WalletId
from src.types.error import Error, error
from src.types.types import AssetType, Currency, TokenStandard, WithdrawalMethod


class TransferType(Base):
    event: WithdrawalMethod
    data: Dict[str, Any]


class ExternalWalletTransferData(Base):
    address: Address
    chain: Chain


class BankTransferData(Base):
    bank_code: str
    bank_name: str
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
    authorization_method: int
    pin: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class WithdrawalRequest(Base):
    asset_id: AssetId
    amount: Decimal
    currency: Currency
    narration: str
    destination: GenericWithdrawalRequest
    authorization: AuthorizationDetails


class AssetPublic(Base):
    asset_id: AssetId = Field(alias="asset-id")
    name: str
    symbol: str
    decimals: int
    asset_type: AssetType = Field(alias="asset-type")
    network: str
    address: str
    standard: Optional[TokenStandard] = None
    is_active: bool = Field(alias="is-active")


class WalletPublic(Base):
    id: WalletId
    address: str
    chain: str
    provider: str
    is_active: bool = Field(alias="is-active")
    assets: List[AssetPublic]


class AssetBalance(Base):
    asset_id: AssetId = Field(alias="asset-id")
    name: str
    symbol: str
    decimals: int
    asset_type: AssetType = Field(alias="asset-type")

    # Balance info
    balance: Optional[Decimal] = None

    # Metadata
    network: str
    address: str
    standard: Optional[TokenStandard] = None
    is_active: bool = Field(alias="is-active")


class WalletWithAssets(Base):
    id: WalletId
    address: str
    chain: str
    provider: str
    is_active: bool = Field(alias="is-active")
    assets: List[AssetBalance]
