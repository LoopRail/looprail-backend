from datetime import datetime
from typing import Any

from pydantic import Field

from src.types.paycrest.base import basePaycrestType
from src.types.types import Currency


class PaycrestRecipiant(basePaycrestType):
    institution: str
    account_identifier: str
    account_name: str
    memo: str
    provider_id: str | None = None
    metadata: dict[str, Any] | None = None
    currency_enum: Currency = Field(
        default=Currency.NAIRA, alias="currency"
    )

    @property
    def currency(self) -> str:
        return self.currency_enum.value


class PaycrestPaymentOrder(basePaycrestType):
    payment_id: str = Field(alias="id")
    amount: str
    token: str
    network: str
    receive_address: str
    valid_until: datetime
    sender_fee: int
    transaction_fee: int
    reference: str
