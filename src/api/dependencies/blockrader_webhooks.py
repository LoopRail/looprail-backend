from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status

from src.infrastructure import config
from src.types.blockrader.webhook_dtos import GenericWebhookEvent, WebhookEvent
from src.utils.auth_utils import verify_signature


async def get_verified_blockrader_webhook(
    request: Request,
    x_blockradar_signature: str = Header(
        ..., alias="X-BlockRadar-Signature", description="BlockRadar Webhook Signature"
    ),
) -> WebhookEvent:
    """
    FastAPI dependency to verify BlockRadar webhook signatures and parse the payload.
    """
    # Get the raw request body
    body = await request.body()

    # Get the secret API key from config
    # Assuming config.block_rader.blockrader_api_key holds the secret
    secret = config.block_rader.blockrader_api_key

    # Verify the signature
    if not verify_signature(body, x_blockradar_signature, secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid BlockRadar webhook signature"},
        )

    # Parse the payload into a generic webhook event
    try:
        generic_event = GenericWebhookEvent.model_validate_json(body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Invalid webhook payload: {e}"},
        )

    # Convert to specific event type
    try:
        specific_event = generic_event.to_specific_event()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Unknown webhook event type: {e}"},
        )

    return specific_event
