from fastapi import APIRouter, Depends, HTTPException, Response

from src.api.dependencies import get_user_usecases
from src.api.dependencies.services import get_resend_service
from src.api.dependencies.usecases import get_otp_usecase
from src.api.rate_limiter import limiter
from src.dtos.otp_dtos import OtpCreate
from src.dtos.user_dtos import UserCreate, UserPublic
from src.infrastructure.logger import get_logger
from src.infrastructure.services.resend_service import ResendService
from src.usecases import OtpUseCase, UserUseCase

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


async def create_user(
    user_data: UserCreate, user_usecases: UserUseCase = Depends(get_user_usecases)
) -> UserPublic:
    """API endpoint to create a new user."""
    created_user, err = await user_usecases.create_user(user_create=user_data)
    if err:
        logger.error("Failed to create user: %s", err.message)
        raise HTTPException(status_code=400, detail=err.message)
    logger.info("User %s registered successfully.", created_user.username)
    return UserPublic.model_validate(created_user)


@router.post("/send-otp")
@limiter.limit("1/minute")
async def send_otp(
    response: Response,
    otp_data: OtpCreate,
    otp_usecases: OtpUseCase = Depends(get_otp_usecase),
    resend_service: ResendService = Depends(get_resend_service),
):
    """API endpoint to send OTP to a user."""

    otp_code, token, err = await otp_usecases.generate_otp(user_email=otp_data.email)
    if err:
        logger.error("Failed to generate OTP: %s", err.message)
        raise HTTPException(status_code=400, detail=err.message)

    _, err = await resend_service.send_otp(
        to=otp_data.email,
        _from="team@looprail.com",
        otp_code=otp_code,
    )
    if err:
        logger.error("Failed to send OTP: %s", err.message)
        raise HTTPException(status_code=500, detail="Failed to send OTP.")

    response.headers["X-OTP-Token"] = token
    logger.info("OTP sent to %s successfully.", otp_data.email)
    return {"message": "OTP sent successfully."}


async def verify_otp():
    pass
