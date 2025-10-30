from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.dtos.base import Base
from src.types import PaymentType, SupportedCurrencies, TransactionStatus


class paymentDetails(BaseModel):
    sender: str = Field(serialization_alias="from")
    receiver: str = Field(serialization_alias="to")
    amount: float
    created_at: datetime


class PaymentStatusResponse(Base):
    payment_id: UUID = Field(serialization_alias="id")
    payment_details: paymentDetails
    status: TransactionStatus
    payment_type: PaymentType
    currency: SupportedCurrencies
    exchange_rate: float
