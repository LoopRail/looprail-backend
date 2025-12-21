from typing import Optional, Tuple

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.dependencies.usecases import (
    get_jwt_usecase,
    get_otp_token,
    get_otp_usecase,
)
from src.api.excpetions import AuthError, OTPError
from src.dtos import VerifyOtpRequest
from src.infrastructure import get_logger
from src.models import Otp
from src.types import Error, OtpStatus
from src.types.access_token_types import AccessToken
from src.usecases import JWTUsecase, OtpUseCase

logger = get_logger(__name__)

type T = AccessToken
security = HTTPBearer(auto_error=False)


class BearerToken[T]:
    async def __call__(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        jwt_usecase: JWTUsecase = Depends(get_jwt_usecase),
    ) -> str:
        """
        FastAPI dependency to validate a Bearer token.
        Raises 401 if missing, invalid, or wrong type.
        """
        if credentials is None:
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Authorization header missing"},
            )

        if credentials.scheme.lower() != "bearer":
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid or expired onboarding token"},
            )

        token = credentials.credentials.strip()
        if not token:
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Token missing"},
            )

        response_token, err = jwt_usecase.verify_access_token(token, T)
        if err:
            raise AuthError(status_code=401, detail={"error": "Invalid token"})

        return response_token


async def verify_otp_dep(
    req: VerifyOtpRequest,
    otp_token: str = Depends(get_otp_token),
    otp_usecases: OtpUseCase = Depends(get_otp_usecase),
) -> Tuple[Optional[Otp], Error]:
    """Verify an OTP against what is stored in Redis."""

    otp, err = await otp_usecases.get_otp(otp_token, req.otp_type)
    if err:
        logger.error("Error getting otp Error: %s", err.detail)
        raise OTPError(status_code=400, detail={"error": "Invalid OTP token"})

    if otp.is_expired():
        otp.status = OtpStatus.EXPIRED
        await otp_usecases.delete_otp(otp_token, req.otp_type.value)
        raise OTPError(status_code=400, detail={"error": "OTP expired"})

    otp.attempts += 1
    if otp.attempts > 3:
        otp.status = OtpStatus.ATTEMPT_EXCEEDED
        await otp_usecases.delete_otp(otp.user_email)
        logger.error("%s exceeded max attempts", otp_token)
        raise OTPError(status_code=400, detail={"error": "Invalid OTP"})

    err = await otp_usecases.update_otp(otp_token, otp)
    if err:
        logger.error("Error updating otp Error: %s", err.detail)
        raise OTPError(status_code=500, detail={"error": "Internal Server Error"})

    is_valid = await otp_usecases.verify_code(req.code, otp.code_hash)
    if not is_valid:
        raise OTPError(status_code=400, detail={"error": "Invalid OTP"})

    otp.status = OtpStatus.USED
    err = await otp_usecases.delete_otp(otp.user_email)
    if err:
        logger.error("Error deleting otp Error: %s", err.detail)
        raise OTPError(status_code=500, detail={"error": "Internal Server Error"})
    return otp
