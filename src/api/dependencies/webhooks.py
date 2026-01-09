from fastapi import Request, status

from src.infrastructure.logger import get_logger
from src.types import httpError
from src.types.blockrader import GenericWebhookEvent, WebhookEvent

logger = get_logger(__name__)


async def get_blockrader_webhook_event(request: Request) -> WebhookEvent:
    body = request.json()

    try:
        generic_event = GenericWebhookEvent.model_validate_json(body)
    except Exception as e:
        error_msg = f"Invalid webhook payload: {e}"
        logger.error(error_msg)
        raise httpError(
            status.HTTP_400_BAD_REQUEST,
            error_msg,
        )

    specific_event = generic_event.to_specific_event()
    if specific_event is None:
        error_msg = f"Unknown webhook event type: {generic_event.event}"
        logger.error(error_msg)
        raise httpError(
            status.HTTP_400_BAD_REQUEST,
            error_msg,
        )
    return specific_event
