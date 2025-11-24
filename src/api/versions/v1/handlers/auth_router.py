from fastapi import (APIRouter, Depends, HTTPException, Request, Response,
                     status)
from fastapi.responses import JSONResponse

from src.api.dependencies import (BearerToken,
                                  get_blockrader_base_wallet_wallet_manager,
                                  get_otp_usecase, get_user_usecases)
# from src.api.rate_limiter import limiter
from src.dtos import OnboardUserUpdate, OtpCreate, UserCreate, UserPublic
from src.infrastructure.logger import get_logger
from src.models import User
from src.types import AccessTokenType, OnBoardingToken
# from src.infrastructure.services.resend_service import ResendService
from src.usecases import OtpUseCase, UserUseCase, WalletManagerUsecase

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/create-user")
# TODO validaet request
async def create_user(
    user_data: UserCreate,
    user_usecases: UserUseCase = Depends(get_user_usecases),
) -> UserPublic:
    """API endpoint to create a new user."""
    created_user, err = await user_usecases.create_user(user_create=user_data)
    if err:
        logger.error("Failed to create user: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Could not create user"},
        )

    logger.info("User %s registered successfully.", created_user.username)
    # TODO send verification email here
    return {
        "user": UserPublic.model_validate(created_user).model_dump_json(
            exclude_none=True
        )
    }


@router.post("/complete_onboarding")
async def complete_onboarding(
    user_data: OnboardUserUpdate,
    token: OnBoardingToken = Depends(BearerToken[OnBoardingToken]),
    user_usecases: UserUseCase = Depends(get_user_usecases),
    base_wallet_usecase: WalletManagerUsecase = Depends(
        get_blockrader_base_wallet_wallet_manager
    ),
):
    if token.token_type != AccessTokenType.ONBOARDING_TOKEN:
        logger.error(
            "Invalid token type expected %s got %s for %s",
            AccessTokenType.ONBOARDING_TOKEN,
            token.token_type,
            token.sub,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid token"},
        )
    current_user, err = await user_usecases.get_user_by_id(user_id=token.user_id)
    _, err = await base_wallet_usecase.create_user_wallet(current_user.id)
    if err:
        logger.error("Failed to create user wallet: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Could not create user wallet"},
        )


@router.post("/send-otp")
# @limiter.limit("1/minute")
async def send_otp(
    request: Request,
    response: Response,
    otp_data: OtpCreate,
    otp_usecases: OtpUseCase = Depends(get_otp_usecase),
    # resend_service: ResendService = Depends(get_resend_service),
):
    """API endpoint to send OTP to a user."""

    _, err = await otp_usecases.get_user_token(user_email=otp_data.email)
    if err and err != "Not found":
        logger.error("Error getting user token %s", err)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Server Error"},
        )
    err = await otp_usecases.delete_otp(user_email=otp_data.email)
    if err and err != "Not found":
        logger.error("Error deleting user token %s", err)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Server Error"},
        )

    otp_code, token, err = await otp_usecases.generate_otp(user_email=otp_data.email)
    if err:
        logger.error("Failed to generate OTP: %s", err)
        raise HTTPException(status_code=400, detail=err.message)

    print(otp_code)
    # _, err = await resend_service.send_otp(
    #     to=otp_data.email,
    #     _from="team@looprail.com",
    #     otp_code=otp_code,
    # )
    # if err:
    #     logger.error("Failed to send OTP: %s", err)
    #     raise HTTPException(status_code=500, detail="Failed to send OTP.")
    #
    response.headers["X-OTP-Token"] = token
    logger.info("OTP sent to %s successfully.", otp_data.email)
    return {"message": "OTP sent successfully."}
