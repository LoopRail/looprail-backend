from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_paycrest_service
from src.infrastructure.services.paycrest.paycrest_service import PaycrestService

router = APIRouter(prefix="/offramp", tags=["Offramp"])


@router.get("/rates")
async def get_rates(
    amount: float = Query(..., description="Amount of token"),
    currency: str = Query(..., description="Target currency (e.g., USD)"),
    paycrest_service: PaycrestService = Depends(get_paycrest_service),
):
    rate, err = await paycrest_service.fetch_letest_usdc_rate(amount, currency)
    if err:
        return JSONResponse(
            status_code=err.code,
            content={"message": err.message},
        )
    return {"rate": rate.data}
