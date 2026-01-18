import hashlib
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, Header, Request, Response, status
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    BearerToken,
    get_app_environment,
    get_config,
    get_current_session,
    get_jwt_usecase,
    get_otp_usecase,
    get_resend_service,
    get_security_usecase,
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
    ChallengeResponse,
    CreateUserResponse,
    LoginRequest,
    MessageResponse,
    OnboardUserUpdate,
    OtpCreate,
    PasscodeLoginRequest,
    PasscodeSetRequest,
    RefreshTokenRequest,
    UserCreate,
    UserPublic,
)
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.services import ResendService
from src.infrastructure.settings import ENVIRONMENT
from src.models import Session
from src.types import (
    AccessToken,
    AccessTokenSub,
    OnBoardingToken,
    Platform,
    TokenType,
    UserAlreadyExistsError,
    UserId,
)
from src.types.common_types import SessionId
from src.usecases import (
    JWTUsecase,
    OtpUseCase,
    SecurityUseCase,
    SessionUseCase,
    UserUseCase,
)

from src.utils.auth_utils import create_refresh_token

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
    if isinstance(err, UserAlreadyExistsError):
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
        user_id=token.user_id.clean()
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
    current_user, err = await user_usecases.complete_user_onboarding(
        user_id=current_user.id,
        transaction_pin=pin_str,
        onboarding_responses=user_data.questioner,
    )
    if err:
        logger.error("Failed to complete user onboarding: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": err.message},
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
        sub=AccessTokenSub.new(session.id),
        user_id=current_user.get_prefixed_id(),
        token_type=TokenType.ACCESS_TOKEN,
        session_id=session.get_prefixed_id(),
        platform=platform,
    )
    access_token = jwt_usecase.create_token(
        data=access_token_data, exp_minutes=config.jwt.access_token_expire_minutes
    )
    return {
        "message": "User onboarded successfully",
        "user": UserPublic.model_validate(current_user).model_dump(exclude_none=True),
        "access-token": access_token,
        "refresh-token": raw_refresh_token,
        "session_id": session.get_prefixed_id(),
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

    session, raw_refresh_token, err = await session_usecase.create_session(
        user_id=user.id,
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
        sub=AccessTokenSub.new(session.id),
        user_id=user.get_prefixed_id(),
        token_type=TokenType.ACCESS_TOKEN,
        session_id=session.get_prefixed_id(),
        platform=platform,
        device_id=device_id,
    )
    access_token = jwt_usecase.create_token(
        data=access_token_data, exp_minutes=config.jwt.access_token_expire_minutes
    )

    return {
        "message": "Login successful.",
        "user": UserPublic.model_validate(user).model_dump(exclude_none=True),
        "access-token": access_token,
        "refresh-token": raw_refresh_token,
        "session_id": session.get_prefixed_id(),
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
        refresh_token_request.refresh_token.clean().encode()
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
            content={"error": "Refresh token reused. Please log in again."},
        )

    session, err = await session_usecase.get_session(refresh_token_db.session_id)
    if err or not session:
        logger.error("Session not found for refresh token %s", refresh_token_db.id)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Session not found."},
        )

    # Issue a new access token
    access_token_data = AccessToken(
        sub=AccessTokenSub.new(session.id),
        token_type=TokenType.ACCESS_TOKEN,
        session_id=session.get_prefixed_id(),
        user_id=UserId.new(session.user_id),
        platform=platform,
        device_id=device_id,
    )
    new_access_token = jwt_usecase.create_token(
        data=access_token_data, exp_minutes=config.jwt.access_token_expire_minutes
    )

    # Issues a new refresh token
    new_raw_refresh_token, err = await session_usecase.rotate_refresh_token(
        old_refresh_token=refresh_token_db,
        new_refresh_token_string=create_refresh_token().clean(),
    )
    if err:
        logger.error("Could not rotate refresh token: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
        )

    return {
        "access-token": new_access_token,
        "refresh-token": new_raw_refresh_token,
    }


@router.post("/challenge", response_model=ChallengeResponse)
@limiter.limit("10/minute")
async def create_challenge(
    request: Request,
    code_challenge: str = Body(..., embed=True),
    security_usecase: SecurityUseCase = Depends(get_security_usecase),
):
    """Generate a PKCE challenge and nonce."""
    challenge, err = await security_usecase.create_challenge(code_challenge)
    if err:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to create challenge"},
        )
    return challenge


@router.post("/passcode/set", response_model=MessageResponse)
@limiter.limit("5/minute")
async def set_passcode(
    request: Request,
    req: PasscodeSetRequest,
    session: Session = Depends(get_current_session),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
):
    """Set a session-bound 6-digit passcode."""
    err = await session_usecase.set_passcode(session.id, req.passcode)
    if err:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to set passcode"},
        )
    return {"message": "Passcode set successfully"}


@router.post("/passcode-login", response_model=AuthWithTokensAndUserResponse)
@limiter.limit("5/minute")
async def passcode_login(
    request: Request,
    req: PasscodeLoginRequest,
    config: Config = Depends(get_config),
    jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
    user_usecases: UserUseCase = Depends(get_user_usecases),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
    security_usecase: SecurityUseCase = Depends(get_security_usecase),
    platform: Platform = Header(...),
    device_id: str = Header(...),
    session_id: SessionId = Header(alias="X-Session-Id"),
):
    verified, err = await security_usecase.verify_pkce(
        req.challenge_id, req.code_verifier
    )
    if err or not verified:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid PKCE challenge or verifier"},
        )

    if not session_id:
        return JSONResponse(
            status_code=400, content={"message": "X-Session-Id header required"}
        )

    valid, err = await session_usecase.verify_passcode(session_id.clean(), req.passcode)
    if err or not valid:
        return JSONResponse(status_code=401, content={"message": "Invalid passcode"})

    session, err = await session_usecase.get_session(session_id.clean())
    if err or not session:
        return JSONResponse(status_code=401, content={"message": "Session not found"})

    access_token_data = AccessToken(
        sub=AccessTokenSub.new(session.id),
        token_type=TokenType.ACCESS_TOKEN,
        session_id=session.get_prefixed_id(),
        user_id=UserId.new(session.user_id),
        platform=platform,
        device_id=device_id,
    )
    access_token = jwt_usecase.create_token(
        data=access_token_data, exp_minutes=config.jwt.access_token_expire_minutes
    )

    refresh_token_id, err = await session_usecase.get_valid_refresh_token(session_id)
    if err or not refresh_token_id:
        return JSONResponse(
            status_code=401, content={"message": "No valid refresh token for session"}
        )

    user, err = await user_usecases.get_user_by_id(session.user_id)
    if err or not user:
        return JSONResponse(status_code=401, content={"message": "User not found"})

    return {
        "message": "Passcode login successful",
        "user": UserPublic.model_validate(user).model_dump(exclude_none=True),
        "access-token": access_token,
        "refresh-token": refresh_token_id,
        "session_id": session.get_prefixed_id(),
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
    err = await session_usecase.revoke_all_user_sessions(current_token.user_id)
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
