from typing import Tuple

from fastapi import Depends, status

from src.api.dependencies.extra_deps import VerifyWebhookRequest
from src.api.dependencies.usecases import get_secrets_usecase
from src.infrastructure.logger import get_logger
from src.types import httpError
from src.types.blockrader import GenericWebhookEvent, WebhookEvent
from src.usecases.secrets_usecases import WebhookProvider

logger = get_logger(__name__)


async def get_blockrader_webhook_event(
    verified_webhook: Tuple[WebhookProvider, bytes] = Depends(
        VerifyWebhookRequest(secrets_usecase=Depends(get_secrets_usecase))
    ),
) -> WebhookEvent:
    provider, body = verified_webhook

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
