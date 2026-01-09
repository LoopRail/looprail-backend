from fastapi import Header, HTTPException, Request, status

from src.infrastructure import config
from src.utils import verify_signature


async def get_blockrader_webhook_event(
    request: Request,
    x_blockradar_signature: str = Header(
        ..., alias="X-BlockRadar-Signature", description="BlockRadar Webhook Signature"
    ),
) -> bool:
    """
    FastAPI dependency to verify BlockRadar webhook signatures.
    """
    # Get the raw request body
    body = await request.body()

    secret = config.block_rader.blockrader_api_key

    # Verify the signature
    if not verify_signature(body, x_blockradar_signature, secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid BlockRadar webhook signature"},
        )
    return True
