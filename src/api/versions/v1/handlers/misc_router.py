import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.dependencies import get_paycrest_service
from src.infrastructure.logger import get_logger
from src.infrastructure.services.paycrest.paycrest_service import PaycrestService

logger = get_logger(__name__)

router = APIRouter(prefix="/misc", tags=["Miscellaneous"])

limiter = Limiter(key_func=get_remote_address)


@router.get("/banks")
@limiter.limit("10/minute")
async def get_supported_banks(request: Request):
    """
    Get all supported banks and their details.
    
    Returns banks data loaded from public/banks.json on app startup.
    Rate limited to 10 requests per minute.
    """
    logger.debug("Fetching supported banks from app state")
    
    banks_data = request.app.state.banks_data
    
    return {
        "status": "success",
        "data": banks_data
    }


@router.get("/rates")
async def get_rates(
    amount: float = Query(..., description="Amount of token"),
    currency: str = Query(..., description="Target currency (e.g., USD)"),
    paycrest_service: PaycrestService = Depends(get_paycrest_service),
):
    """Get exchange rates for USDC to target currency."""
    logger.info("Fetching rates for amount %s %s", amount, currency)
    rate, err = await paycrest_service.fetch_letest_usdc_rate(amount, currency)
    if err:
        logger.error(
            "Error fetching rates for amount %s %s: %s", amount, currency, err.message
        )
        return JSONResponse(
            status_code=err.code,
            content={"message": err.message},
        )
    logger.info(
        "Successfully fetched rates for amount %s %s: %s", amount, currency, rate.data
    )
    return {"rate": round(float(rate.data), 2)}
