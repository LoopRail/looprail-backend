from datetime import datetime
from uuid import uuid4
from decimal import Decimal

from sqlalchemy import Integer, String, ForeignKey, TIMESTAMP, text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    # one-to-many relationship
    wallets: Mapped[list["Wallet"]] = relationship("Wallet", back_populates="user")
    payment_orders: Mapped[list["PaymentOrder"]] = relationship(
        "PaymentOrder", back_populates="user"
    )


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    address: Mapped[str] = mapped_column(String, unique=True, index=True)
    type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    # many-to-one relationship
    user: Mapped["User"] = relationship("User", back_populates="wallets")


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4()), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    order_id: Mapped[str] = mapped_column(String, nullable=False)

    # many-to-one relationship
    user: Mapped["User"] = relationship("User", back_populates="payment_orders")
