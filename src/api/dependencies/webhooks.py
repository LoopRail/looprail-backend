from typing import Tuple

from fastapi import Depends, HTTPException, status

from src.api.dependencies.extra_deps import VerifyWebhookRequest
from src.api.dependencies.usecases import get_secrets_usecase
from src.types.blockrader import GenericWebhookEvent, WebhookEvent
from src.usecases.secrets_usecases import WebhookProvider
from src.types import error


async def get_blockrader_webhook_event(
    verified_webhook: Tuple[WebhookProvider, bytes] = Depends(
        VerifyWebhookRequest(secrets_usecase=Depends(get_secrets_usecase))
    ),
) -> WebhookEvent:
    provider, body = verified_webhook

    try:
        generic_event = GenericWebhookEvent.model_validate_json(body)
    except Exception as e:
        raise error(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid webhook payload: {e}",
        )

    specific_event = generic_event.to_specific_event()
    if specific_event is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Unknown webhook event type: {generic_event.event}"},
        )
    return specific_event
