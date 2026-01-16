from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_paycrest_service
from src.api.versions.v1.handlers import (
    accounts_router,
    auth_router,
    transactions_router,
    verify_router,
    wallet_router,
    webhook_router,
)
from src.infrastructure.services.paycrest.paycrest_service import PaycrestService
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)

v1_router = APIRouter(prefix="/v1")


@v1_router.get("/rates", tags=["Miscellaneous"])
async def get_rates(
    amount: float = Query(..., description="Amount of token"),
    currency: str = Query(..., description="Target currency (e.g., USD)"),
    paycrest_service: PaycrestService = Depends(get_paycrest_service),
):
    logger.info("Fetching rates for amount %s %s", amount, currency)
    rate, err = await paycrest_service.fetch_letest_usdc_rate(amount, currency)
    if err:
        logger.error("Error fetching rates for amount %s %s: %s", amount, currency, err.message)
        return JSONResponse(
            status_code=err.code,
            content={"message": err.message},
        )
    logger.info("Successfully fetched rates for amount %s %s: %s", amount, currency, rate.data)
    return {"rate": round(float(rate.data), 2)}


v1_router.include_router(auth_router.router)
v1_router.include_router(accounts_router.router)
v1_router.include_router(transactions_router.router)
v1_router.include_router(wallet_router.router)
v1_router.include_router(verify_router.router)
v1_router.include_router(webhook_router.router)
