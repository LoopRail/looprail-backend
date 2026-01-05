from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import add_rate_limiter, v1_router
from src.api.middlewares import RequestLoggerMiddleware
from src.infrastructure import RedisClient, config
from src.infrastructure.db import get_session
from src.infrastructure.services import (
    AuthLockService,
    PaycrestService,
    PaystackService,
    ResendService,
)
from src.types import Error, error


@asynccontextmanager
async def lifespan(app_: FastAPI):
    app_.state.redis = RedisClient(config.redis)

    app_.state.paycrest = PaycrestService(config.paycrest)
    app_.state.paystack = PaystackService(config.paystack)
    app_.state.resend = ResendService(config.resend)

    app_.state.auth_lock = AuthLockService(redis_client=app.state.redis)

    app_.state.blockrader_config = config.block_rader

    yield
    
    # --- SHUTDOWN ---
    # await app_.state.redis.close()  # if async


app = FastAPI(
    title="Looprail Backend",
    description="LoopRail's backend service",
    version="0.1.0",
    lifespan=lifespan,
)

add_rate_limiter(app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggerMiddleware)
app.include_router(v1_router, prefix="/api")


@app.exception_handler(error)
async def custom_error_handler(request: Request, exc: Error):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": exc.message},
    )


@app.exception_handler(HTTPException)
async def custom_http_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
