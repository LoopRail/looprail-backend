from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.infrastructure.redis import RQManager
from src.api.dependencies import get_paycrest_service, get_rq_manager
from src.infrastructure.logger import get_logger
from src.infrastructure.services.paycrest.paycrest_service import PaycrestService
from src.types.bank import SupportedBanksResponse
from src.types.types import Currency
from services.notifications.tasks import send_push_notification_task
from src.dtos.notification_dtos import PushNotificationDTO
from pydantic import BaseModel

logger = get_logger(__name__)

router = APIRouter(prefix="/misc", tags=["Miscellaneous"])

limiter = Limiter(key_func=get_remote_address)


@router.get("/banks", response_model=SupportedBanksResponse)
@limiter.limit("10/minute")
async def get_supported_banks(request: Request):
    """
    Get all supported banks and their details.

    Rate limited to 10 requests per minute.
    """
    logger.debug("Fetching supported banks from app state")

    banks_data = request.app.state.banks_data

    return {"status": "success", "data": banks_data}


@router.get("/rates")
async def get_rates(
    amount: float = Query(..., description="Amount of token"),
    currency: Currency = Query(..., description="Target currency (e.g., USD)"),
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

from pydantic import BaseModel

class TestPushRequest(BaseModel):
    token: str

@router.post("/test-push")
async def test_push_notification(
    request: TestPushRequest,
    rq_manager: RQManager = Depends(get_rq_manager)
):
    """
    Test endpoint to send a push notification immediately with just a token, bypassing background tasks.
    """
    logger.info(f"Test push notification request received for token: {request.token}")
    try:
        # Create a dummy notification with the provided token
        notification = PushNotificationDTO(
            user_id="test_user",
            title="Test Push Notification",
            body="This is a test message to verify push notification delivery.",
            token=request.token
        )
        
        # Enqueue the push notification task
        job = rq_manager.get_queue().enqueue(
            send_push_notification_task,
            notification.model_dump()
        )
        
        return {"status": "success", "message": "Test push notification enqueued successfully", "job_id": job.id}
    except Exception as e:
        logger.exception("Exception in test push notification endpoint")
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error during test push queueing", "error": str(e)}
        )
