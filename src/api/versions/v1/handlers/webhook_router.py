from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import VerifyWebhookRequest, get_secrets_usecase
from src.infrastructure.logger import get_logger
from src.types.blockrader import GenericWebhookEvent
from src.usecases.secrets_usecases import WebhookProvider

logger = get_logger(__name__)

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhook"],
    dependencies=Depends(
        VerifyWebhookRequest(secrets_usecase=Depends(get_secrets_usecase))
    ),
)


@router.post("/blockrader", status_code=status.HTTP_200_OK)
async def handle_blockrader_webhook(
    verified_webhook: Tuple[WebhookProvider, bytes] = Depends(),
):
    provider, body = verified_webhook

    try:
        generic_event = GenericWebhookEvent.model_validate_json(body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Invalid webhook payload: {e}"},
        )

    specific_event = generic_event.to_specific_event()
    if specific_event is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Unknown webhook event type: {generic_event.event}"},
        )

    logger.info("Received BlockRadar webhook event: %s", specific_event.event)
    # Here you would typically process the webhook_event
    # e.g., update database, trigger other services, etc.
    return {"message": "Webhook received and processed"}
