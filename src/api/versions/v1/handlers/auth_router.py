from fastapi import (APIRouter, Depends, HTTPException, Request, Response,
                     status)
from fastapi.responses import JSONResponse

from src.api.dependencies import (get_otp_token, get_otp_usecase,
                                  get_resend_service, get_user_usecases)
from src.api.rate_limiter import limiter
from src.dtos import OtpCreate, UserCreate, UserPublic, VerifyOtpRequest
from src.infrastructure.logger import get_logger
from src.infrastructure.services.resend_service import ResendService
from src.models.otp_model import Otp
from src.types import OtpStatus
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
    request: Request,
    response: Response,
    otp_data: OtpCreate,
    otp_usecases: OtpUseCase = Depends(get_otp_usecase),
    resend_service: ResendService = Depends(get_resend_service),
):
    """API endpoint to send OTP to a user."""

    token, err = await otp_usecases.get_user_token(user_email=otp_data.email)

    if err and err != "Not found":
        logger.error("Error getting user token %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Server Error"},
        )
    err = await otp_usecases.delete_otp(user_email=otp_data.email)
    if err:
        logger.error("Error deleting user token %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Server Error"},
        )

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


@router.post("/verify-otp")
@limiter.limit("1/minute")
async def verify_otp(
    request: Request,
    req: VerifyOtpRequest,
    otp: Otp = Depends(get_otp_token),
    otp_usecases: OtpUseCase = Depends(get_otp_usecase),
):
    """Verify an OTP against what is stored in Redis."""
    token, err = otp_usecases.get_user_token(otp.user_email)
    if err:
        logger.error(err.message)
        raise HTTPException(status_code=400, detail="Invlaid OTP Token")

    if otp.is_expired():
        otp.status = OtpStatus.EXPIRED
        otp_usecases.delete_otp(token, req.otp_type.value)
        raise HTTPException(status_code=400, detail="OTP expired")

    if otp.verify_code(req.code):
        otp.status = OtpStatus.USED
        otp_usecases.delete_otp(otp.user_email, req.otp_type)
        return {"message": "OTP verified successfully"}

    if otp.attempts > 3:
        otp.status = OtpStatus.ATTEMPT_EXCEEDED
        otp_usecases.delete_otp(otp.e, req.otp_type.value)
        raise HTTPException(status_code=400, detail="Too many attempts")

    otp.attempts += 1

    err = otp_usecases.update_otp(otp.tok)
    if err:
        logger.error(err.message)
        raise HTTPException(status_code=500, detail="Internal server error")

    raise HTTPException(status_code=400, detail="Invalid OTP")
