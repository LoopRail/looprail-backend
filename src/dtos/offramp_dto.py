from decimal import Decimal

from src.dtos.base import Base


class GenerateAddressRequest(Base):
    label: str
    callbackUrl: str | None = None


class AddressData(Base):
    address: str


class GenerateAddressResponse(Base):
    data: AddressData


class OrderRequest(Base):
    user_id: int
    token: str
    network: str
    amount: Decimal
    recipient: dict
    reference: str
    return_address: str


class OrderResponse(Base):
    user_id: int
    order_id: str
    amount: Decimal
    receive_address: str
    sender_fee: Decimal
    transaction_fee: Decimal
    valid_until: str


class OffRampRequest(Base):
    user_id: int
    token: str
    amount: Decimal
    network: str
    recipient: dict
    reference: str
    return_address: str


class OffRampResponse(Base):
    data: dict
