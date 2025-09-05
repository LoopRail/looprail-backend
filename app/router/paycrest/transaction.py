from fastapi import APIRouter, HTTPException
from ...services.paycrest.paycrest_status import check_order_status

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("/{order_id}")
def get_transaction(order_id: str):
    """Fetch current status of an order by polling Paycrest API."""
    try:
        order = check_order_status(order_id)
        return {"data": order}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
