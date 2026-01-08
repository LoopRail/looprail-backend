import hmac
import hashlib
import time
from typing import Callable, Optional, Tuple

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.infrastructure.logger import get_logger
from src.types import httpError
from src.usecases.secrets_usecases import SecretsUsecase, WebhookProvider
from src.utils import verify_signature

logger = get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        logger.info(
            "Request: %s %s \nClient: %s\nHeaders: %s \nQuery: %s",
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
            dict(request.headers),
            dict(request.query_params),
        )

        # Process the request
        response = await call_next(request)

        # Calculate processing time
        process_time = (time.time() - start_time) * 1000
        formatted_time = f"{process_time:.2f}ms"

        logger.info(
            "Response: %s %s \nStatus: %s \nTime: %s",
            request.method,
            request.url.path,
            response.status_code,
            formatted_time,
        )

        # Add X-Process-Time header
        response.headers["X-Process-Time"] = formatted_time

        return response


class VerifyWebhookRequest:
    def __init__(self, secrets_usecase: SecretsUsecase) -> None:
        self.secrets_usecase = secrets_usecase

    async def __call__(self, request: Request) -> Tuple[WebhookProvider, bytes]:
        body = await request.body()
        
        provider = self._detect_provider(request.headers, request)
        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Unknown webhook provider or missing signature header"},
            )

        signature = request.state.webhook_signature
        secret = self.secrets_usecase.get(provider)
        
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": f"Webhook not allowed for provider {provider.value}"},
            )

        if not self._verify_signature(provider, body, secret, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid webhook signature"},
            )

        return provider, body

    def _detect_provider(self, headers, request: Request) -> Optional[WebhookProvider]:
        if "X-BlockRadar-Signature" in headers:
            # Store signature in request.state for later use
            request.state.webhook_signature = headers.get("X-BlockRadar-Signature")
            # TODO: Add origin checking here (e.g., IP whitelisting)
            return WebhookProvider.BLOCKRADER
        # Add other providers here
        return None

    def _verify_signature(self, provider: WebhookProvider, body: bytes, secret: str, signature: str) -> bool:
        if provider == WebhookProvider.BLOCKRADER:
            return verify_signature(body, signature, secret)
        # Add verification logic for other providers
        return False
