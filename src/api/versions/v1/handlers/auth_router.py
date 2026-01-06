import hashlib
from typing import Callable

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    BearerToken,
    get_jwt_usecase,
    get_otp_usecase,
    get_session_usecase,
    get_user_usecases,
    get_wallet_manager_factory,
)

# from src.api.rate_limiter import limiter
from src.api.internals import send_otp_internal
from src.dtos import (
    LoginRequest,
    OnboardUserUpdate,
    OtpCreate,
    RefreshTokenRequest,
    UserCreate,
    UserPublic,
)
from src.dtos.auth_dtos import (
    AuthTokensResponse,
    AuthWithTokensAndUserResponse,
    CreateUserResponse,
    MessageResponse,
)
from src.infrastructure import config
from src.infrastructure.logger import get_logger
from src.types import AccessToken, Chain, OnBoardingToken, Platform, TokenType
from src.usecases import (
    JWTUsecase,
    OtpUseCase,
    SessionUseCase,
    UserUseCase,
    WalletManagerUsecase,
)
from src.utils import validate_password_strength

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/create-user", response_model=CreateUserResponse)
# @limiter.limit("2/minute")
async def create_user(
    user_data: UserCreate,
    user_usecases: UserUseCase = Depends(get_user_usecases),
    otp_usecases: OtpUseCase = Depends(get_otp_usecase),
) -> dict:
    validation_error = validate_password_strength(user_data.password)
    if validation_error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": validation_error.message},
        )
    created_user, err = await user_usecases.create_user(user_create=user_data)
    if err:
        logger.error("Failed to create user: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Could not create user"},
        )
    token = await send_otp_internal(
        email=created_user.email,
        otp_usecases=otp_usecases,
    )

    logger.info("User %s registered successfully.", created_user.username)

    return {
        "user": UserPublic.model_validate(created_user.model_dump()).model_dump(
            exclude_none=True
        ),
        "otp_token": token,
    }


@router.post(
    "/complete_onboarding",
    response_model=AuthWithTokensAndUserResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
# @limiter.limit("2/minute")
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
    platform: Platform = Header(..., alias="X-Platform"),
    jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
):
    if token.token_type != TokenType.ONBOARDING_TOKEN:
        logger.error(
            "Invalid token type expected %s got %s for %s",
            TokenType.ONBOARDING_TOKEN,
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
        active_wallets = [w for w in config.block_rader.wallets if w.active]
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

    session, raw_refresh_token = await session_usecase.create_session(
        user_id=current_user.id,
        device_id=device_id,
        platform=platform,
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
    access_token_data = AccessToken(
        sub=current_user.id,
        token_type=TokenType.ACCESS_TOKEN,
        session_id=session.id,
        platform=platform,
    )
    access_token = jwt_usecase.create_token(
        data=access_token_data, exp_minutes=config.jwt.access_token_expire_minutes
    )
    return {
        "message": "User onboarded successfully, wallet creation in progress.",
        "user": UserPublic.model_validate(current_user.model_dump()).model_dump(
            exclude_none=True
        ),
        "access-token": access_token,
        "refresh-token": raw_refresh_token,
    }


@router.post("/login", response_model=AuthWithTokensAndUserResponse)
# @limiter.limit("2/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    user_usecases: UserUseCase = Depends(get_user_usecases),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
    device_id: str = Header(..., alias="X-Device-ID"),
    platform: str = Header(..., alias="X-Platform"),
    jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
):
    user, err = await user_usecases.authenticate_user(
        email=login_request.email, password=login_request.password
    )
    if err:
        logger.error(
            "Authentication failed for user %s: %s", login_request.email, err.message
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid credentials"},
        )

    session, raw_refresh_token = await session_usecase.create_session(
        user_id=user.id,
        device_id=device_id,
        platform=platform,
        ip_address=request.client.host,
    )
    if err:
        logger.error("Could not create session for user %s: %s", user.id, err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )

    access_token_data = AccessToken(
        sub=user.id,
        token_type=TokenType.ACCESS_TOKEN,
        session_id=session.id,
        platform=platform,
        device_id=device_id,
    )
    access_token = jwt_usecase.create_token(
        data=access_token_data, exp_minutes=config.jwt.access_token_expire_minutes
    )

    return {
        "message": "Login successful.",
        "user": UserPublic.model_validate(user.model_dump()).model_dump(
            exclude_none=True
        ),
        "access-token": access_token,
        "refresh-token": raw_refresh_token,
    }


@router.post(
    "/token", summary="Refresh Access Token", response_model=AuthTokensResponse
)
# @limiter.limit("2/minute")
async def refresh_token(
    request: Request,
    refresh_token_request: RefreshTokenRequest,
    session_usecase: SessionUseCase = Depends(get_session_usecase),
    jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
    device_id: str = Header(..., alias="X-Device-ID"),
    platform: Platform = Header(..., alias="X-Platform"),
):
    incoming_refresh_token_hash = hashlib.sha256(
        refresh_token_request.refresh_token.encode()
    ).hexdigest()

    refresh_token_db, err = await session_usecase.get_valid_refresh_token_by_hash(
        incoming_refresh_token_hash
    )
    if err or not refresh_token_db:
        logger.error(
            "Invalid or expired refresh token: %s", err.message if err else "Not found"
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid or expired refresh token"},
        )

    if refresh_token_db.replaced_by_hash is not None:
        logger.warning(
            "Refresh token reuse detected for session %s", refresh_token_db.session_id
        )
        await session_usecase.revoke_session(refresh_token_db.session_id)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Refresh token reused. Please log in again."},
        )

    # Get the session details
    session, err = await session_usecase.get_session(refresh_token_db.session_id)
    if err or not session:
        logger.error("Session not found for refresh token %s", refresh_token_db.id)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Session not found."},
        )

    # Rotate the refresh token
    new_raw_refresh_token = jwt_usecase.create_refresh_token()
    _, err = await session_usecase.rotate_refresh_token(
        old_refresh_token=refresh_token_db,
        new_refresh_token_string=new_raw_refresh_token,
    )
    if err:
        logger.error(
            "Failed to rotate refresh token for session %s: %s", session.id, err.message
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error during token rotation"},
        )

    # Issue a new access token
    access_token_data = AccessToken(
        sub=session.user_id,
        token_type=TokenType.ACCESS_TOKEN,
        session_id=session.id,
        platform=platform,
        device_id=device_id,
    )
    new_access_token = jwt_usecase.create_token(
        data=access_token_data, exp_minutes=config.jwt.access_token_expire_minutes
    )

    return {
        "access-token": new_access_token,
        "refresh-token": new_raw_refresh_token,
    }


@router.post(
    "/logout", summary="Logout from current session", response_model=MessageResponse
)
# @limiter.limit("2/minute")
async def logout(
    current_token: AccessToken = Depends(BearerToken[AccessToken]),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
):
    err = await session_usecase.revoke_session(current_token.session_id)
    if err:
        logger.error(
            "Failed to revoke session %s for user %s: %s",
            current_token.session_id,
            current_token.sub,
            err.message,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to logout"},
        )
    return {"message": "Logged out successfully"}


@router.post(
    "/logout-all", summary="Logout from all sessions", response_model=MessageResponse
)
# @limiter.limit("2/minute")
async def logout_all(
    current_token: AccessToken = Depends(BearerToken[AccessToken]),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
):
    err = await session_usecase.revoke_all_user_sessions(current_token.sub)
    if err:
        logger.error(
            "Failed to revoke all sessions for user %s: %s",
            current_token.sub,
            err.message,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to logout from all sessions"},
        )
    return {"message": "Logged out from all sessions successfully"}


@router.post("/send-otp", response_model=MessageResponse)
# @limiter.limit("1/minute")
async def send_otp(
    response: Response,
    otp_data: OtpCreate,
    otp_usecases: OtpUseCase = Depends(get_otp_usecase),
):
    token = await send_otp_internal(
        email=otp_data.email,
        otp_usecases=otp_usecases,
    )

    response.headers["X-OTP-Token"] = token
    return {"message": "OTP sent successfully"}
