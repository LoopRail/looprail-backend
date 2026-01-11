from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter

from src.dtos import PaymentStatusResponse, paymentDetails
from src.infrastructure.logger import get_logger
from src.types import Currency, PaymentType, TransactionStatus

logger = get_logger(__name__)

router = APIRouter(prefix="/wallets", tags=["Payment"])


@router.get("/{payment_id}/status")
async def get_payment_status(payment_id: str):
    dummy_details = paymentDetails(
        sender="sender_address_123",
        receiver="Andrew Oluwatomiwo David",
        amount=100.4,
        created_at=datetime.now(),
    )
    dummy_data = PaymentStatusResponse(
        payment_id=uuid4(),
        payment_details=dummy_details,
        status=TransactionStatus.COMPLETED,
        payment_type=PaymentType.FIAT,
        currency=Currency.NAIRA,
        exchange_rate=1500.0,
    )
    return dummy_data
