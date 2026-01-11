from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_paycrest_service
from src.infrastructure.logger import get_logger
from src.infrastructure.services import PaycrestService
from src.types.paycrest import CreateOrderRequest

logger = get_logger(__name__)


router = APIRouter(prefix="/transactions", tags=["Offramp"])


@router.post("/withdraw")
async def withdraw_funds(
    request: CreateOrderRequest,
    paycrest_service: PaycrestService = Depends(get_paycrest_service),
):
    # TODO add metadata or user id
    order, err = await paycrest_service.create_payment_order(
        amount=Decimal(request.amount),
        recipient=request.recipient,
        reference="",  # TODO put some thing here from the db
        return_address="",  # TODO put something here
    )

    if err:
        logger.error("Could not create payment order Error: %s", err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create payment order",
        )
    return order.model_dump()


@router.post("/external-wallet")
async def withdraw_to_external_wallet():
    pass


@router.post("/process-order")
def process_order():
    pass
