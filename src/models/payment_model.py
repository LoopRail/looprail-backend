from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Numeric, String
from sqlmodel import Field, Relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.user_model import User


class PaymentOrder(Base, table=True):
    __tablename__ = "payment_orders"
    __protected_fields__ = "all"
    __id_prefix__ = "pmt_"

    user_id: str = Field(foreign_key="users.id", index=True)
    amount: Decimal = Field(Numeric(18, 2), nullable=False)
    order_id: str = Field(String, nullable=False)
    user: User = Relationship(back_populates="payment_orders")


# TODO do we need to add the users wallet here to
