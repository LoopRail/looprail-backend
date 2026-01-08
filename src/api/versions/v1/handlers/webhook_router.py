from fastapi import APIRouter, Depends, status

from src.api.dependencies.blockrader_webhooks import get_verified_blockrader_webhook
from src.infrastructure.logger import get_logger
from src.types.blockrader.webhook_dtos import WebhookEvent

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhook"])

@router.post("/blockrader", status_code=status.HTTP_200_OK)
async def handle_blockrader_webhook(
    webhook_event: WebhookEvent = Depends(get_verified_blockrader_webhook),
):
    logger.info("Received BlockRadar webhook event: %s", webhook_event.event)
    # Here you would typically process the webhook_event
    # e.g., update database, trigger other services, etc.
    return {"message": "Webhook received and processed"}
