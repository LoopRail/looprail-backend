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
    currency_enum: Currency = Field(default=Currency.NAIRA, alias="currency")

    @property
    def currency(self) -> str:
        return self.currency_enum.value


class PaycrestProviderAccount(basePaycrestType):
    network: str
    receive_address: str
    valid_until: datetime


class PaycrestPaymentOrder(basePaycrestType):
    """v2 order response shape."""

    payment_id: str = Field(alias="id")
    amount: str
    rate: str
    sender_fee: str
    transaction_fee: str
    reference: str
    provider_account: PaycrestProviderAccount

    @property
    def receive_address(self) -> str:
        """Convenience accessor kept for backward compat with existing call sites."""
        return self.provider_account.receive_address
