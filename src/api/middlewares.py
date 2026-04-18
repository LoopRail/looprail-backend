import os
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.infrastructure.logger import get_logger
from src.infrastructure.settings import ENVIRONMENT

logger = get_logger(__name__)


REDACTED_HEADERS = {"authorization", "x-api-key", "cookie", "set-cookie"}


def _redact_headers(headers: dict) -> dict:
    if os.getenv("ENVIRONMENT") != ENVIRONMENT.PRODUCTION.value:
        return headers
    return {
        k: "**redacted**" if k.lower() in REDACTED_HEADERS else v
        for k, v in headers.items()
    }
    return {
        k: "**redacted**" if k.lower() in REDACTED_HEADERS else v
        for k, v in headers.items()
    }


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        logger.info(
            "Request: %s %s \nClient: %s\nHeaders: %s \nQuery: %s",
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
            _redact_headers(dict(request.headers)),
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
