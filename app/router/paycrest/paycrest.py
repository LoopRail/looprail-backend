from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from ...database import get_db
from ...services.paycrest.paycrest_service import PaycrestService
from ....schemas.service_schema import OrderRequest, OrderResponse

router = APIRouter(prefix="/paycrest", tags=["Paycrest"])

service = PaycrestService()

@router.post("/order", response_model=OrderResponse)
async def payout_to_bank(request: OrderRequest, db: Session = Depends(get_db)):
    service = PaycrestService(db)
    try:
        return await service.create_payment_order(
            user_id=request.user_id,
            token=request.token,
            amount=Decimal(request.amount),
            network=request.network,
            recipient=request.recipient,
            reference=request.reference,
            return_address=request.return_address
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
