import hashlib

from fastapi import APIRouter, Body, Depends, Header, Request, Response, status
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    BearerToken,
    get_app_environment,
    get_auth_lock_service,
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
from src.api.rate_limiters import custom_rate_limiter, limiter
from src.dtos import (
    AuthTokensResponse,
    AuthWithTokensAndUserResponse,
    ChallengeResponse,
    CompleteOnboardingRequest,
    CreateUserResponse,
    LoginRequest,
    MessageResponse,
    OtpCreate,
    PasscodeLoginRequest,
    PasscodeSetRequest,
    RefreshTokenRequest,
    SetTransactionPinRequest,
    UserCreate,
)
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.services import AuthLockService, ResendService
from src.infrastructure.settings import ENVIRONMENT
from src.models import Session
from src.types import (
    AccessToken,
    AccessTokenSub,
    OnBoardingToken,
    OnBoardingTokenSub,
    Platform,
    TokenType,
    UserAlreadyExistsError,
    UserId,
)
from src.types.common_types import DeviceID, SessionId
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

login_auth_lock = get_auth_lock_service("logins")


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

    public_user, err = await user_usecases.load_public_user(created_user.id)
    if err:
        logger.error(
            "Failed to load public user data for %s: %s", created_user.id, err.message
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to load user data"},
        )

    logger.info("Create user flow completed for %s. OTP token issued.", user_data.email)
    return {
        "user": public_user,
        "otp_token": token,
    }


@router.post(
    "/setup-wallet",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
async def setup_wallet(
    request: Request,
    user_data: SetTransactionPinRequest,
    token: OnBoardingToken = Depends(BearerToken[OnBoardingToken](OnBoardingToken)),
    user_usecases: UserUseCase = Depends(get_user_usecases),
):
    logger.info("Setting up wallet for user ID: %s", token.user_id)
    if token.token_type != TokenType.ONBOARDING_TOKEN:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid token"},
        )

    _, err = await user_usecases.setup_user_wallet(
        user_id=token.user_id.clean(),
        transaction_pin=user_data.transaction_pin,
    )
    if err:
        logger.error(
            "Failed to setup user wallet for user %s: %s", token.user_id, err.message
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": err.message},
        )

    logger.info("Wallet setup successfully initiated for user ID: %s", token.user_id)
    return {"message": "Wallet setup initiated successfully"}


@router.post(
    "/complete_onboarding",
    response_model=AuthWithTokensAndUserResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("5/minute")
async def complete_onboarding(
    request: Request,
    user_data: CompleteOnboardingRequest,
    token: OnBoardingToken = Depends(BearerToken[OnBoardingToken](OnBoardingToken)),
    user_usecases: UserUseCase = Depends(get_user_usecases),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
    device_id: DeviceID = Header(..., alias="X-Device-ID"),
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

    current_user, err = await user_usecases.finalize_onboarding(
        user_id=current_user.id,
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
    public_user, err = await user_usecases.load_public_user(current_user.id)
    if err:
        logger.error(
            "Failed to load public user data during onboarding for %s: %s",
            current_user.id,
            err.message,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to load user data"},
        )

    logger.info("Onboarding successfully completed for user ID: %s", current_user.id)
    return {
        "message": "User onboarded successfully",
        "session_id": session.get_prefixed_id(),
        "refresh-token": raw_refresh_token,
        "access-token": access_token,
        "user": public_user,
    }


@router.post("/login", response_model=AuthWithTokensAndUserResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    user_usecases: UserUseCase = Depends(get_user_usecases),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
    device_id: DeviceID = Header(..., alias="X-Device-ID"),
    platform: Platform = Header(..., alias="X-Platform"),
    jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
    config: Config = Depends(get_config),
    auth_lock_service: AuthLockService = Depends(login_auth_lock),
):
    logger.info("Received login request for email: %s", login_request.email)
    login_request.ip_address = request.client.host
    login_request.user_agent = request.headers.get("user-agent")

    is_locked, err = await auth_lock_service.is_account_locked(login_request.email)
    if err or is_locked:
        logger.warning(
            "Account locked for user %s due to too many failed attempts. IP: %s, User-Agent: %s",
            login_request.email,
            login_request.ip_address,
            login_request.user_agent,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Account is locked due to too many failed attempts."},
        )
    user, err = await user_usecases.authenticate_user(
        email=login_request.email, password=login_request.password
    )
    if err:
        current_attempts, _ = await auth_lock_service.increment_failed_attempts(
            user.email
        )
        logger.warning(
            "Invalid password for user %s. Failed attempts: %s. IP: %s, User-Agent: %s",
            login_request.email,
            current_attempts,
            login_request.ip_address,
            login_request.user_agent,
        )
        logger.error("Authentication failed for user %s: %s", login_request.email, err)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid credentials"},
        )
    await auth_lock_service.reset_failed_attempts(user.email)

    public_user, err = await user_usecases.load_public_user(user.id)
    if err:
        logger.error(
            "Failed to load public user data during login for %s: %s",
            user.id,
            err.message,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to load user data"},
        )

    if not user.has_completed_onboarding:
        logger.info(
            "User %s has not completed onboarding. Issuing onboarding token.",
            login_request.email,
        )
        token_data = OnBoardingToken(
            sub=OnBoardingTokenSub.new(user.id), user_id=user.get_prefixed_id()
        )
        onboarding_token = jwt_usecase.create_token(
            data=token_data, exp_minutes=config.jwt.onboarding_token_expire_minutes
        )
        return {
            "message": "Login successful. Please complete onboarding.",
            "user": public_user,
            "access-token": onboarding_token,
        }

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

    logger.info(
        "User %s logged in successfully. Session created: %s",
        login_request.email,
        session.get_prefixed_id(),
    )
    return {
        "message": "Login successful.",
        "session_id": session.get_prefixed_id(),
        "access-token": access_token,
        "refresh-token": raw_refresh_token,
        "user": public_user,
    }


@router.post(
    "/token", summary="Refresh Access Token", response_model=AuthTokensResponse
)
@limiter.limit("3/minute")
async def refresh_token(
    request: Request,
    refresh_token_request: RefreshTokenRequest,
    device_id: DeviceID = Header(..., alias="X-Device-ID"),
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

    new_refresh_token = create_refresh_token()

    # Issues a new refresh token
    err = await session_usecase.rotate_refresh_token(
        old_refresh_token=refresh_token_db,
        new_refresh_token_string=new_refresh_token.clean(),
    )
    if err:
        logger.error(
            "Could not rotate refresh token for session %s: %s", session.id, err.message
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
        )

    logger.info(
        "Access token refreshed successfully for session: %s", session.get_prefixed_id()
    )
    return {"access-token": new_access_token, "refresh-token": new_refresh_token}


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
        logger.error("Failed to create PKCE challenge: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to create challenge"},
        )
    logger.info("PKCE challenge created successfully.")
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
        logger.error(
            "Failed to set passcode for session %s: %s", session.id, err.message
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to set passcode"},
        )
    logger.info("Passcode set successfully for session: %s", session.get_prefixed_id())
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
    auth_lock_service: AuthLockService = Depends(login_auth_lock),
    device_id: DeviceID = Header(..., alias="X-Device-ID"),
    platform: Platform = Header(..., alias="X-Platform"),
    session_id: SessionId = Header(alias="X-Session-Id"),
):
    req.ip_address = request.client.host
    req.user_agent = request.headers.get("user-agent")
    logger.info(
        "Passcode login attempt for session ID: %s. IP: %s, User-Agent: %s",
        session_id,
        req.ip_address,
        req.user_agent,
    )

    if not session_id:
        logger.warning(
            "Passcode login attempt without X-Session-Id header. IP: %s, User-Agent: %s",
            req.ip_address,
            req.user_agent,
        )
        return JSONResponse(
            status_code=400, content={"message": "X-Session-Id header required"}
        )

    session, err = await session_usecase.get_session(session_id.clean())
    if err or not session:
        logger.error(
            "Session not found for session ID %s during passcode login. IP: %s, User-Agent: %s",
            session_id,
            req.ip_address,
            req.user_agent,
        )
        return JSONResponse(status_code=401, content={"message": "Session not found"})

    user, err = await user_usecases.get_user_by_id(session.user_id)
    if err or not user:
        logger.error(
            "User not found for user ID %s during passcode login. Session ID: %s. IP: %s, User-Agent: %s",
            session.user_id,
            session_id,
            req.ip_address,
            req.user_agent,
        )
        return JSONResponse(status_code=401, content={"message": "User not found"})

    verified, err = await security_usecase.verify_pkce(
        req.challenge_id, req.code_verifier
    )
    if err or not verified:
        logger.warning(
            "PKCE verification failed for passcode login for user ID: %s. IP: %s, User-Agent: %s",
            user.id,
            req.authorization.ip_address,
            req.authorization.user_agent,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid PKCE challenge or verifier"},
        )

    # Check if account is locked
    is_locked, err = await auth_lock_service.is_account_locked(
        user.email,
    )
    if err or is_locked:
        logger.warning(
            "Account locked for user %s (email: %s) due to too many failed passcode attempts. IP: %s, User-Agent: %s",
            user.id,
            user.email,
            req.authorization.ip_address,
            req.authorization.user_agent,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Account is locked due to too many failed attempts."},
        )

    valid, err = await session_usecase.verify_passcode(session_id.clean(), req.passcode)
    if err or not valid:
        current_attempts, _ = await auth_lock_service.increment_failed_attempts(
            user.email,
        )
        logger.warning(
            "Invalid passcode for user %s (email: %s). Failed attempts: %s. IP: %s, User-Agent: %s",
            user.id,
            user.email,
            current_attempts,
            req.authorization.ip_address,
            req.authorization.user_agent,
        )
        return JSONResponse(status_code=401, content={"message": "Invalid passcode"})

    # Reset failed attempts on successful PIN verification
    await auth_lock_service.reset_failed_attempts(user.email)

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

    public_user, err = await user_usecases.load_public_user(user.id)
    if err:
        logger.error(
            "Failed to load public user data during passcode login for %s: %s",
            user.id,
            err.message,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to load user data"},
        )

    logger.info(
        "Passcode login successful for session: %s, user: %s. IP: %s, User-Agent: %s",
        session.get_prefixed_id(),
        user.id,
        req.authorization.ip_address,
        req.authorization.user_agent,
    )
    return {
        "message": "Passcode login successful",
        "session_id": session.get_prefixed_id(),
        "access-token": access_token,
        "user": public_user,
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
    err = await session_usecase.revoke_session(current_token.session_id.clean())
    if err:
        logger.error(
            "Failed to revoke session %s for user %s: %s",
            current_token.session_id,
            current_token.user_id,
            err.message,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to logout"},
        )
    logger.info("Logout successful for session: %s", current_token.session_id)
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
    err = await session_usecase.revoke_all_user_sessions(current_token.user_id.clean())
    if err:
        logger.error(
            "Failed to revoke all sessions for user %s: %s",
            current_token.user_id,
            err.message,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Failed to logout from all sessions"},
        )
    logger.info("Logged out from all sessions for user: %s", current_token.user_id)
    return {"message": "Logged out from all sessions successfully"}


@router.post("/send-otp", response_model=MessageResponse)
@custom_rate_limiter("otp", identifier_arg="otp_data", identifier_field="email")
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
    logger.info("OTP sent successfully to email: %s", otp_data.email)
    return {"message": "OTP sent successfully"}
