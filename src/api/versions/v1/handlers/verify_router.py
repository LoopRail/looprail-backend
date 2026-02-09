from fastapi import APIRouter, Depends, Request, status

from src.api.dependencies import (
    get_config,
    get_jwt_usecase,
    get_user_usecases,
    verify_otp_dep,
)
from src.api.rate_limiters import limiter
from src.dtos import OTPSuccessResponse
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.models import Otp
from src.types import AuthError, NotFoundError, OnBoardingToken, OtpType
from src.types.common_types import OnBoardingTokenSub
from src.usecases import JWTUsecase, UserUseCase

logger = get_logger(__name__)

router = APIRouter(prefix="/verify", tags=["Auth", "Verify"])


@router.post("/onboarding-otp")
@limiter.limit("1/minute")
async def verify_onboarding_otp(
    request: Request,
    otp: Otp = Depends(verify_otp_dep),
    config: Config = Depends(get_config),
    jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
    user_usecase: UserUseCase = Depends(get_user_usecases),
):
    logger.info("Verifying onboarding OTP for user email %s", otp.user_email)
    if otp.otp_type != OtpType.ONBOARDING_EMAIL_VERIFICATION:
        logger.error("Invalid OTP type for onboarding verification")
        raise AuthError(code=status.HTTP_400_BAD_REQUEST, message="Invalid otp type")
    user, err = await user_usecase.get_user_by_email(user_email=otp.user_email)
    if err == NotFoundError:
        logger.error(
            "Could not find user with email: %s, Error: %s", otp.user_email, err
        )
        raise AuthError(code=status.HTTP_404_NOT_FOUND, message="user not found")

    user.is_email_verified = True
    user, err = await user_usecase.save(user)
    if err:
        logger.error("Could not update user: Error: %s", err)
        raise AuthError(code=status.HTTP_404_NOT_FOUND, message="user not found")

    data = OnBoardingToken(
        sub=OnBoardingTokenSub.new(user.id), user_id=user.get_prefixed_id()
    )
    access_token = jwt_usecase.create_token(
        data=data, exp_minutes=config.jwt.onboarding_token_expire_minutes
    )
    return OTPSuccessResponse(
        message="OTP verified successfully", access_token=access_token
    )
