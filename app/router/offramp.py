from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from ..database import get_db
from ..services.blockradar.blockradar_service import BlockradarService
from ..services.paycrest.paycrest_service import PaycrestService
from ..services.paycrest.paycrest_contract import send_to_paycrest
from ...schemas.service_schema import OffRampRequest, OffRampResponse
from ..models import Wallet

router = APIRouter(prefix="/offramp", tags=["OffRamp"])

@router.post("/", response_model=OffRampResponse)
async def offramp_funds(request: OffRampRequest, db: Session = Depends(get_db)):
    blockradar = BlockradarService(db)
    paycrest = PaycrestService(db)

    # Get user wallet
    wallet: Wallet = db.query(Wallet).filter(Wallet.user_id == request.user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    try:
        # Sweep funds from wallet to treasury if disableAutoSweep == False
        treasury_tx_hash = await blockradar.sweep_to_treasury(wallet, request.amount)

        # Create an off-ramp payment order
        order = await paycrest.create_payment_order(
            user_id=request.user_id,
            token=request.token,
            amount=Decimal(request.amount),
            network=request.network,
            recipient=request.recipient,
            reference=request.reference,
            return_address=request.return_address
        )

        # Execute payout via Paycrest contract (returns tx hash string)
        paycrest_tx_hash = send_to_paycrest(order)

        return OffRampResponse(
            data={
                "status": "success",
                "user": order.user_id,
                "order_id": order.order_id,
                "amount": str(order.amount),
                "receive_address": order.receive_address,
                "sender_fee": order.sender_fee,
                "transaction_fee": order.transaction_fee,
                "valid_until": order.valid_until,
                "treasury_tx_hash": treasury_tx_hash,
                "paycrest_tx_hash": paycrest_tx_hash,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))