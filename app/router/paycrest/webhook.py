from fastapi import APIRouter, Request, HTTPException, Depends, status
from sqlalchemy.orm import Session
import hmac
import hashlib
import logging

from ...settings import settings
from ...database import get_db
from ...models import PaymentOrder

router = APIRouter(prefix="/webhook", tags=["Webhook"])
logger = logging.getLogger(__name__)


def verify_paycrest_signature(request_body: bytes, signature_header: str, secret_key: str) -> bool:
    """Verify HMAC SHA-256 signature from Paycrest webhook."""
    key = secret_key.encode("utf-8")
    expected_signature = hmac.new(key, request_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header, expected_signature)


@router.post("/", status_code=status.HTTP_200_OK)
async def webhook_listener(request: Request, db: Session = Depends(get_db)):
    """Receive and validate webhook events from Paycrest."""
    signature = request.headers.get("X-Paycrest-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing X-Paycrest-Signature header")

    body = await request.body()
    if not verify_paycrest_signature(body, signature, settings.paycrest_api_key):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = data.get("event")
    order_data = data.get("data", {})
    order_id = order_data.get("id")

    if not event or not order_id:
        raise HTTPException(status_code=400, detail="Missing event or order ID in payload")

    # Update the order status in DB
    order = db.query(PaymentOrder).filter(PaymentOrder.id == order_id).first()
    if not order:
        logger.warning(f"Webhook for unknown order: {order_id}")
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = event
    db.commit()

    logger.info(f"Order {order_id} updated to status {event}")

    return {"status": "ok", "order_id": order_id, "event": event}
