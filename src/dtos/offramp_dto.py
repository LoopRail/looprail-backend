from decimal import Decimal

from pydantic import BaseModel


class GenerateAddressRequest(BaseModel):
    label: str
    callbackUrl: str | None = None


class AddressData(BaseModel):
    address: str


class GenerateAddressResponse(BaseModel):
    data: AddressData


class OrderRequest(BaseModel):
    user_id: int
    token: str
    network: str
    amount: Decimal
    recipient: dict
    reference: str
    return_address: str


class OrderResponse(BaseModel):
    user_id: int
    order_id: str
    amount: Decimal
    receive_address: str
    sender_fee: Decimal
    transaction_fee: Decimal
    valid_until: str


class OffRampRequest(BaseModel):
    user_id: int
    token: str
    amount: Decimal
    network: str
    recipient: dict
    reference: str
    return_address: str


class OffRampResponse(BaseModel):
    data: dict
