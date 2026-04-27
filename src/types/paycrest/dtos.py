from decimal import Decimal

from src.types.paycrest.base import basePaycrestResponse, basePaycrestType
from src.types.paycrest.types import PaycrestPaymentOrder, PaycrestRecipiant


class GenerateAddressRequest(basePaycrestType):
    label: str
    callbackUrl: str | None = None


class AddressData(basePaycrestType):
    address: str


class GenerateAddressResponse(basePaycrestResponse):
    data: AddressData


class OrderRequest(basePaycrestType):
    user_id: int
    token: str
    network: str
    amount: Decimal
    recipient: dict
    reference: str
    return_address: str


# v2 nested source/destination objects
class OrderSource(basePaycrestType):
    type: str = "crypto"
    currency: str
    network: str
    refund_address: str


class OrderDestinationRecipient(basePaycrestType):
    institution: str
    account_identifier: str
    account_name: str
    memo: str


class OrderDestination(basePaycrestType):
    type: str = "fiat"
    currency: str
    recipient: OrderDestinationRecipient


class CreateOrderRequest(basePaycrestType):
    amount: Decimal
    source: OrderSource
    destination: OrderDestination
    reference: str


class CreateOrderResponse(basePaycrestResponse):
    data: PaycrestPaymentOrder


# v2 rates: data is {buy: {rate, ...}, sell: {rate, ...}}
class RateQuote(basePaycrestType):
    rate: str
    provider_ids: list[str] = []
    order_type: str | None = None
    refund_timeout_minutes: int | None = None


class RatesData(basePaycrestType):
    buy: RateQuote | None = None
    sell: RateQuote | None = None


class FetchLatestRatesResponse(basePaycrestResponse):
    data: RatesData
