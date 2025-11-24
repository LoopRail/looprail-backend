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


class CreateOrderRequest(basePaycrestType):
    amount: Decimal
    recipient: PaycrestRecipiant

class CreateOrderResponse(basePaycrestResponse):
    data: PaycrestPaymentOrder


class FetchLatestRatesResponse(basePaycrestResponse):
    data: str
