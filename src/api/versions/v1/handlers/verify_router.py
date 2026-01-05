from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from src.api.dependencies import get_jwt_usecase, get_user_usecases, verify_otp_dep

# from src.api.rate_limiter import limiter
from src.dtos import OTPSuccessResponse
from src.infrastructure import config
from src.infrastructure.logger import get_logger
from src.models import Otp
from src.types import NotFoundError, OnBoardingToken, OtpType
from src.usecases import JWTUsecase, UserUseCase

logger = get_logger(__name__)

router = APIRouter(prefix="/verify", tags=["Auth", "Verify"])


@router.post("/onbaording-otp")
# @limiter.limit("1/minute")
async def verify_onboarding_otp(
    request: Request,
    jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
    user_usecase: UserUseCase = Depends(get_user_usecases),
    otp: Otp = Depends(verify_otp_dep),
):
    if otp.otp_type != OtpType.ONBOARDING_EMAIL_VERIFICATION:
        logger.error("Invalid OTP type for onboarding verification")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content="Invalid otp type"
        )
    user, err = await user_usecase.get_user_by_email(email=otp.user_email)
    if err == NotFoundError:
        logger.error(
            "Could not find user with email: %s, Error: %s", otp.user_email, err
        )
        return JSONResponse(
            code=status.HTTP_404_NOT_FOUND, content={"error": "user not found"}
        )

    user.is_email_verified = True
    user, err = user_usecase.save(user)
    if err:
        logger.error("Could not update user: Error: %s", err)
        return JSONResponse(
            code=status.HTTP_404_NOT_FOUND, content={"error": "user not found"}
        )
    data = OnBoardingToken(sub=user.id, user_id=user.id)
    access_token = jwt_usecase.create_access_token(
        data=data, exp_minutes=config.jwt.onboarding_token_expire_minutes
    )
    return OTPSuccessResponse(
        message="OTP verified successfully", access_token=access_token
    )
