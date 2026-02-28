from fastapi import Depends, Request, status

from src.api.dependencies import get_verify_webhook_request
from src.infrastructure.logger import get_logger
from src.types import httpError, WebhookProvider
from src.types.blockrader import GenericWebhookEvent, WebhookEvent

logger = get_logger(__name__)


async def get_blockrader_webhook_event(
    request: Request,
    verify: WebhookProvider = Depends(get_verify_webhook_request),
) -> WebhookEvent:
    logger.debug("Entering get_blockrader_webhook_event")
    # Verify signature before processing
    await verify(request)

    body = await request.json()
    try:
        generic_event = GenericWebhookEvent.model_validate(body)
    except Exception as e:
        error_msg = "Invalid webhook payload: %s"
        logger.error(error_msg, e)
        raise httpError(
            status.HTTP_400_BAD_REQUEST,
            error_msg,
        ) from e

    specific_event, err = generic_event.to_specific_event()
    if err:
        error_msg = "Unknown webhook event type: %s"
        logger.error(error_msg, generic_event.event)
        raise httpError(
            status.HTTP_400_BAD_REQUEST,
            error_msg,
        )
    return specific_event
