import hashlib

from fastapi import APIRouter, Body, Depends, Header, Request, Response, status
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    BearerToken,
    get_app_environment,
    get_config,
    get_jwt_usecase,
    get_otp_usecase,
    get_resend_service,
    get_session_usecase,
    get_user_usecases,
)
from src.api.internals import (
    send_otp_internal,
    set_send_otp_config,
    set_user_create_config,
)
from src.api.rate_limiter import limiter
from src.dtos import (
    AuthTokensResponse,
    AuthWithTokensAndUserResponse,
    CreateUserResponse,
    LoginRequest,
    MessageResponse,
    OnboardUserUpdate,
    OtpCreate,
    RefreshTokenRequest,
    UserCreate,
    UserPublic,
)
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.services import ResendService
from src.infrastructure.settings import ENVIRONMENT
from src.types import (
    AccessToken,
    OnBoardingToken,
    Platform,
    TokenType,
    UserAlreadyExistsError,
)
from src.usecases import JWTUsecase, OtpUseCase, SessionUseCase, UserUseCase
from src.utils import create_refresh_token

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/create-user", response_model=CreateUserResponse)
@limiter.limit("5/minute")
async def create_user(
    request: Request,
    _config_set: None = Depends(set_user_create_config),
    user_data: UserCreate = Body(...),
    environment: ENVIRONMENT = Depends(get_app_environment),
    user_usecases: UserUseCase = Depends(get_user_usecases),
    otp_usecases: OtpUseCase = Depends(get_otp_usecase),
    resend_service: ResendService = Depends(get_resend_service),
) -> dict:
    logger.info("Received create user request for email: %s", user_data.email)
    created_user, err = await user_usecases.create_user(user_create=user_data)
    if type(err) is type(UserAlreadyExistsError()):
        logger.error("Failed to create user: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": err.message},
        )
    if err:
        logger.error("Failed to create user: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Could not create user"},
        )
    token = await send_otp_internal(
        environment,
        email=created_user.email,
        otp_usecases=otp_usecases,
        resend_service=resend_service,
    )

    logger.info("User %s registered successfully.", created_user.email)

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
@limiter.limit("5/minute")
async def complete_onboarding(
    request: Request,
    user_data: OnboardUserUpdate,
    token: OnBoardingToken = Depends(BearerToken[OnBoardingToken](OnBoardingToken)),
    user_usecases: UserUseCase = Depends(get_user_usecases),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
    device_id: str = Header(..., alias="X-Device-ID"),
    platform: Platform = Header(..., alias="X-Platform"),
    jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
    config: Config = Depends(get_config),
):
    logger.info("Completing onboarding for user ID: %s", token.user_id)
    if token.token_type != TokenType.ONBOARDING_TOKEN:
        logger.error(
            "Invalid token type expected %s got %s for %s",
            TokenType.ONBOARDING_TOKEN,
            token.token_type,
            token.sub,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid token"},
        )

    current_user, err = await user_usecases.get_user_by_id(
        user_id=token.get_clean_user_id()
    )
    if err:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "User not found"},
        )
    if current_user.has_completed_onboarding:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Onboarding already completed"},
        )

    pin_str = "".join(map(str, user_data.transaction_pin))
    _, err = await user_usecases.update_transaction_pin(current_user.id, pin_str)
    if err:
        logger.error("Could not set transaction pin: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
        )

    _, err = await user_usecases.update_user(
        current_user.id, has_completed_onboarding=True
    )
    if err:
        logger.error("Could not update user: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
        )

    session, raw_refresh_token, err = await session_usecase.create_session(
        user_id=current_user.id,
        device_id=device_id,
        platform=platform,
        ip_address=request.client.host,
        allow_notifications=user_data.allow_notifications,
    )
    if err:
        logger.error(
            "Could not create session for user %s: %s", current_user.id, err.message
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
        )
    access_token_data = AccessToken(
        sub=current_user.get_prefixed_id(),
        token_type=TokenType.ACCESS_TOKEN,
        session_id=session.get_prefixed_id(),
        platform=platform,
    )
    access_token = jwt_usecase.create_token(
        data=access_token_data, exp_minutes=config.jwt.access_token_expire_minutes
    )
    return {
        "message": "User onboarded successfully",
        "user": UserPublic.model_validate(current_user.model_dump()).model_dump(
            exclude_none=True
        ),
        "access-token": access_token,
        "refresh-token": raw_refresh_token,
    }


@router.post("/login", response_model=AuthWithTokensAndUserResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    user_usecases: UserUseCase = Depends(get_user_usecases),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
    device_id: str = Header(..., alias="X-Device-ID"),
    platform: str = Header(..., alias="X-Platform"),
    jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
    config: Config = Depends(get_config),
):
    logger.info("Received login request for email: %s", login_request.email)
    user, err = await user_usecases.authenticate_user(
        email=login_request.email, password=login_request.password
    )
    if err:
        logger.error("Authentication failed for user %s: %s", login_request.email, err)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid credentials"},
        )

    session, raw_refresh_token = await session_usecase.create_session(
        user_id=user.get_prefixed_id(),
        device_id=device_id,
        platform=platform,
        ip_address=request.client.host,
    )
    if err:
        logger.error("Could not create session for user %s: %s", user.id, err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
        )

    access_token_data = AccessToken(
        sub=user.get_prefixed_id(),
        user_id=user.get_prefixed_id(),
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
@limiter.limit("2/minute")
async def refresh_token(
    request: Request,
    refresh_token_request: RefreshTokenRequest,
    device_id: str = Header(..., alias="X-Device-ID"),
    platform: Platform = Header(..., alias="X-Platform"),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
    jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
    config: Config = Depends(get_config),
):
    logger.info("Received refresh token request from device ID: %s", device_id)
    incoming_refresh_token_hash = hashlib.sha256(
        refresh_token_request.get_clean_refresh_token().encode()
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
            content={"message": "Invalid or expired refresh token"},
        )

    if refresh_token_db.replaced_by_hash is not None:
        logger.warning(
            "Refresh token reuse detected for session %s", refresh_token_db.session_id
        )
        await session_usecase.revoke_session(refresh_token_db.session_id)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Refresh token reused. Please log in again."},
        )

    # Get the session details
    session, err = await session_usecase.get_session(refresh_token_db.session_id)
    if err or not session:
        logger.error("Session not found for refresh token %s", refresh_token_db.id)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Session not found."},
        )

    # Rotate the refresh token
    new_raw_refresh_token = create_refresh_token()
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
            content={"message": "Internal server error during token rotation"},
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
@limiter.limit("5/minute")
async def logout(
    request: Request,
    current_token: AccessToken = Depends(BearerToken[AccessToken](AccessToken)),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
):
    logger.info("Received logout request for session ID: %s", current_token.session_id)
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
            content={"message": "Failed to logout"},
        )
    return {"message": "Logged out successfully"}


@router.post(
    "/logout-all", summary="Logout from all sessions", response_model=MessageResponse
)
@limiter.limit("5/minute")
async def logout_all(
    request: Request,
    current_token: AccessToken = Depends(BearerToken[AccessToken](AccessToken)),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
):
    logger.info(
        "Received logout all sessions request for user ID: %s", current_token.sub
    )
    err = await session_usecase.revoke_all_user_sessions(current_token.sub)
    if err:
        logger.error(
            "Failed to revoke all sessions for user %s: %s",
            current_token.sub,
            err.message,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to logout from all sessions"},
        )
    return {"message": "Logged out from all sessions successfully"}


@router.post("/send-otp", response_model=MessageResponse)
@limiter.limit("1/minute")
async def send_otp(
    request: Request,
    response: Response,
    otp_data: OtpCreate,
    _config_set: None = Depends(set_send_otp_config),
    environment: ENVIRONMENT = Depends(get_app_environment),
    otp_usecases: OtpUseCase = Depends(get_otp_usecase),
    resend_service: ResendService = Depends(get_resend_service),
):
    token = await send_otp_internal(
        environment,
        email=otp_data.email,
        otp_usecases=otp_usecases,
        resend_service=resend_service,
    )

    response.headers["X-OTP-Token"] = token
    return {"message": "OTP sent successfully"}
