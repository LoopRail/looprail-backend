from typing import Callable

import httpx
from fastapi import (APIRouter, BackgroundTasks, Depends, Header,
                     HTTPException, Request, Response, status)
from fastapi.responses import JSONResponse

from src.api.dependencies import (BearerToken, get_otp_usecase,
                                  get_session_usecase, get_user_usecases,
                                  get_wallet_manager_factory)
# from src.api.rate_limiter import limiter
from src.dtos import OnboardUserUpdate, OtpCreate, UserCreate, UserPublic
from src.infrastructure.logger import get_logger
from src.infrastructure.settings import block_rader_config
from src.types import AccessTokenType, Chain, OnBoardingToken
# from src.infrastructure.services.resend_service import ResendService
from src.usecases import OtpUseCase, UserUseCase, WalletManagerUsecase, SessionUseCase

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/create-user")
# @limiter.limit("2/minute")
async def create_user(
    request: Request,
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
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

    async def trigger_send_otp():
        """Triggers the send_otp endpoint in the background."""
        url = request.url_for("send_otp")
        async with httpx.AsyncClient(base_url=request.base_url) as client:
            try:
                await client.post(url, json={"email": created_user.email})
            except httpx.RequestError as e:
                logger.error("HTTPX error calling send_otp: %s", e)

    background_tasks.add_task(trigger_send_otp)

    logger.info("User %s registered successfully.", created_user.username)
    return {
        "user": UserPublic.model_validate(created_user).model_dump_json(
            exclude_none=True
        )
    }


@router.post("/complete_onboarding")
async def complete_onboarding(
    request: Request,
    user_data: OnboardUserUpdate,
    background_tasks: BackgroundTasks,
    token: OnBoardingToken = Depends(BearerToken[OnBoardingToken]),
    user_usecases: UserUseCase = Depends(get_user_usecases),
    wallet_manager_factory: Callable[[Chain], WalletManagerUsecase] = Depends(
        get_wallet_manager_factory
    ),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
    device_id: str = Header(..., alias="X-Device-ID"),
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
    if err:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "User not found"},
        )
    _, err = await user_usecases.update_user_profile(current_user.id, **user_data)
    if err:
        logger.error("Could not update user: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )
    _, err = await user_usecases.update_user(
        current_user.id, has_completed_onboarding=True
    )
    if err:
        logger.error("Could not update user: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )

    async def create_wallets_in_background(user_id):
        active_wallets = [w for w in block_rader_config.wallets if w.active]
        for wallet_config in active_wallets:
            wallet_manager = wallet_manager_factory(wallet_config.chain)
            if not wallet_manager:
                logger.warning(
                    "No wallet manager for chain %s, skipping.", wallet_config.chain
                )
                continue

            _, err = await wallet_manager.create_user_wallet(user_id)
            if err:
                logger.error(
                    "Failed to create user wallet for chain %s: %s",
                    wallet_config.chain,
                    err.message,
                )
                continue

    background_tasks.add_task(create_wallets_in_background, current_user.id)

    session, err = await session_usecase.create_session(
        user=UserPublic.model_validate(current_user),
        device_id=device_id,
        ip_address=request.client.host,
    )
    if err:
        logger.error(
            "Could not create session for user %s: %s", current_user.id, err.message
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": "User onboarded successfully, wallet creation in progress.",
            "session_id": str(session.session_id),
        },
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
