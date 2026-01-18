from decimal import Decimal
from typing import Any, Dict, Optional, Tuple, Type

from pydantic import field_validator

from src.dtos.base import Base
from src.types.common_types import Address, AssetId, Chain
from src.types.error import Error, error
from src.types.types import PaymentMethod, WithdrawalMethod


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


class WithdrawalRequest(Base):
    asset_id: AssetId
    amount: Decimal
    narration: str
    destination: GenericWithdrawalRequest

    def get_clean_asset_id(self):
        return self.asset_id.removeprefix("ast_")


class ProcessWithdrawalRequest(Base):
    transaction_id: str
    transation_pin: str
