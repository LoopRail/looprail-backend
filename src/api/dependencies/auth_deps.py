from typing import Optional, Tuple

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.dependencies.usecases import (
    get_jwt_usecase,
    get_otp_token,
    get_otp_usecase,
    get_user_usecases,
)
from src.dtos import VerifyOtpRequest
from src.infrastructure import get_logger
from src.models import Otp, User
from src.types import (
    AccessToken,
    AuthError,
    Error,
    InternaleServerError,
    OTPError,
    OtpStatus,
    TokenType,
    httpError,
)
from src.usecases import JWTUsecase, OtpUseCase, UserUseCase
from src.usecases.secrets_usecases import SecretsUsecase, WebhookProvider
from src.utils import verify_signature

logger = get_logger(__name__)

security = HTTPBearer(auto_error=False)


class BearerToken[T]:
    def __init__(self, response_model: T) -> None:
        self.response_model = response_model

    async def __call__(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
    ) -> T:
        logger.debug("Entering BearerToken.__call__")
        """
        FastAPI dependency to validate a Bearer token.
        Raises 401 if missing, invalid, or wrong type.
        """
        if credentials is None:
            raise AuthError(
                code=status.HTTP_401_UNAUTHORIZED,
                message="Authorization header missing",
            )

        if credentials.scheme.lower() != "bearer":
            raise AuthError(
                code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid or expired onboarding token",
            )

        token = credentials.credentials.strip()
        if not token:
            raise AuthError(
                code=status.HTTP_401_UNAUTHORIZED,
                message="Token missing",
            )

        response_token, err = jwt_usecase.verify_token(token, self.response_model)
        if err:
            raise AuthError(code=401, message="Invalid token")

        return response_token


async def get_current_user_token(
    token: AccessToken = Depends(BearerToken[AccessToken](AccessToken)),
) -> AccessToken:
    logger.debug("Entering get_current_user_token")
    if token.token_type != TokenType.ACCESS_TOKEN:
        raise AuthError(code=401, message="User not found")
    return token


async def get_current_user(
    access_token: AccessToken = Depends(get_current_user_token),
    user_usecase: UserUseCase = Depends(get_user_usecases),
) -> User:
    logger.debug("Entering get_current_user for user ID: %s", access_token.sub)
    user, err = await user_usecase.get_user_by_id(access_token.sub)
    if err:
        raise AuthError(code=401, message="User not found")
    return user


async def verify_otp_dep(
    req: VerifyOtpRequest,
    otp_token: str = Depends(get_otp_token),
    otp_usecases: OtpUseCase = Depends(get_otp_usecase),
) -> Tuple[Optional[Otp], Error]:
    logger.info("Verifying OTP dependency for token: %s", otp_token)
    """Verify an OTP against what is stored in Redis."""

    otp, err = await otp_usecases.get_otp(otp_token, req.otp_type)
    if err:
        logger.error("Error getting otp Error: %s", err)
        raise OTPError("Invalid OTP token")

    if otp.is_expired():
        otp.status = OtpStatus.EXPIRED
        err = await otp_usecases.delete_otp(otp.user_email)
        if err:
            logger.error("Could not delete OTP %s Error %s", otp_token, err)
        raise OTPError("OTP expired")

    otp.attempts += 1
    if otp.attempts > 30:
        otp.status = OtpStatus.ATTEMPT_EXCEEDED
        err = await otp_usecases.delete_otp(otp.user_email)
        if err:
            logger.error("Could not delete OTP %s Error %s", otp_token, err)
        logger.error("%s exceeded max attempts", otp_token)
        raise OTPError("Invalid OTP")

    err = await otp_usecases.update_otp(otp_token, otp)
    if err:
        logger.error("Error updating otp Error: %s", err)
        raise InternaleServerError

    is_valid = await otp_usecases.verify_code(req.code, otp.code_hash)
    if not is_valid:
        raise OTPError("Invalid OTP")

    otp.status = OtpStatus.USED
    err = await otp_usecases.delete_otp(otp.user_email)
    if err:
        logger.error("Error deleting otp Error: %s", err)
        raise InternaleServerError
    return otp


class VerifyWebhookRequest:
    def __init__(self, secrets_usecase: SecretsUsecase) -> None:
        self.secrets_usecase = secrets_usecase

    async def __call__(self, request: Request) -> Tuple[WebhookProvider, bytes]:
        logger.debug("Entering VerifyWebhookRequest.__call__")
        body = await request.body()

        provider = self._detect_provider(request.headers, request)
        if provider is None:
            error_msg = "Unknown webhook provider or missing signature header"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": error_msg},
            )

        signature = request.state.webhook_signature
        secret = self.secrets_usecase.get(provider)

        if not secret:
            error_msg = f"Webhook not allowed for provider {provider.value}"
            logger.error(error_msg)
            raise httpError(
                code=status.HTTP_403_FORBIDDEN,
                message=error_msg,
            )

        if not self._verify_signature(provider, body, secret, signature):
            error_msg = "Invalid webhook signature"
            logger.error(error_msg)
            raise httpError(status.HTTP_401_UNAUTHORIZED, message=error_msg)

        return provider

    def _detect_provider(self, headers, request: Request) -> Optional[WebhookProvider]:
        logger.debug("Entering _detect_provider")
        if "X-BlockRadar-Signature" in headers:
            request.state.webhook_signature = headers.get("X-BlockRadar-Signature")
            # TODO: Add origin checking here (e.g., IP whitelisting)
            return WebhookProvider.BLOCKRADER
        return None

    def _verify_signature(
        self, provider: WebhookProvider, body: bytes, secret: str, signature: str
    ) -> bool:
        logger.debug("Entering _verify_signature for provider: %s", provider.value)
        if provider == WebhookProvider.BLOCKRADER:
            return verify_signature(body, signature, secret)
        return False
