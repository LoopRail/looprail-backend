import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic_core import ValidationError as PydanticValidationError

from src.api import add_rate_limiter, v1_router
from src.api.middlewares import RequestLoggerMiddleware
from src.infrastructure import RedisClient, get_logger, load_config
from src.infrastructure.services import (
    AuthLockService,
    LedgerService,
    PaycrestService,
    PaystackService,
    ResendService,
)
from src.types import Error, InternaleServerError, error

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    config = load_config()
    app_.state.config = config
    app_.state.environment = config.app.environment

    app_.state.redis = RedisClient(config.redis)

    app_.state.paycrest = PaycrestService(config.paycrest)
    app_.state.paystack = PaystackService(config.paystack)
    app_.state.resend = ResendService(config.resend)
    app_.state.ledger_service = LedgerService(config.ledger)

    app_.state.auth_lock = AuthLockService(redis_client=app.state.redis)

    app_.state.blockrader_config = config.block_rader
    app_.state.ledger_config = config.ledger
    app_.state.argon2_config = config.argon2

    app_.state.banks_data = config.banks_data.root # Access the loaded data

    yield

    # --- SHUTDOWN ---
    # await app_.state.redis.close()  # if async


app = FastAPI(
    title="Looprail Backend",
    description="LoopRail's backend service",
    version="0.1.0",
    lifespan=lifespan,
    # docs_url=None,
    # redoc_url=None,
)

add_rate_limiter(app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["looprail.xyz"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggerMiddleware)
app.include_router(v1_router, prefix="/api")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles Pydantic's validation errors to return a human-readable message.
    """
    error_details = exc.errors()
    logger.error(error_details)

    messages = []
    for e in error_details:
        loc_parts = e.get("loc", [])[1:]
        # Filter out pydantic-internal validation details from the location path
        filtered_loc = [str(p) for p in loc_parts if "[" not in str(p)]
        field_path = ".".join(filtered_loc)
        message = e.get("msg")

        if message:
            # Clean up pydantic's 'Value error, ' prefix if it exists
            if "Value error, " in message:
                message = message.replace("Value error, ", "")

            if field_path:
                messages.append(f"{field_path}: {message}")
            else:
                messages.append(message)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"messages": messages},
    )


@app.exception_handler(PydanticValidationError)
async def raw_pydantic_validation_exception_handler(
    request: Request, exc: PydanticValidationError
):
    """
    Handles raw Pydantic validation errors that might occur outside of FastAPI's RequestValidationError.
    """
    error_details = exc.errors()
    logger.error(error_details)

    messages = []
    for e in error_details:
        loc_parts = e.get("loc", [])[1:]
        # Filter out pydantic-internal validation details from the location path
        filtered_loc = [str(p) for p in loc_parts if "[" not in str(p)]
        field_path = ".".join(filtered_loc)
        message = e.get("msg")

        if message:
            if "Value error, " in message:
                message = message.replace("Value error, ", "")

            if field_path:
                messages.append(f"{field_path}: {message}")
            else:
                messages.append(message)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"message": messages},
    )


@app.exception_handler(error)
async def custom_error_handler(request: Request, exc: Error):
    logger.error(exc.message)
    code = status.HTTP_400_BAD_REQUEST
    if hasattr(exc, "code"):
        code = exc.code
    return JSONResponse(
        status_code=code,
        content={"message": exc.message},
    )


@app.exception_handler(HTTPException)
async def custom_http_error_handler(request: Request, exc: HTTPException):
    # Log the HTTPException details
    logger.error(
        "HTTPException caught: Status Code: %s, Detail: %s, Headers: %s",
        exc.status_code,
        exc.detail,
        exc.headers,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": InternaleServerError.message},
    )


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    return {"status": "ok"}
