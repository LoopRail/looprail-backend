from fastapi import HTTPException

from src.infrastructure import config
from src.infrastructure.logger import get_logger
from src.infrastructure.services import ResendService
from src.infrastructure.settings import ENVIRONMENT
from src.usecases import OtpUseCase

logger = get_logger(__name__)


async def send_otp_internal(
    email: str,
    otp_usecases: OtpUseCase,
    resend_service: ResendService,
) -> str:
    _, err = await otp_usecases.get_user_token(user_email=email)
    if err and err != "Not found":
        raise HTTPException(status_code=500, detail="Server Error")

    err = await otp_usecases.delete_otp(user_email=email)
    if err and err != "Not found":
        raise HTTPException(status_code=500, detail="Server Error")

    otp_code, token, err = await otp_usecases.generate_otp(user_email=email)
    if err:
        raise HTTPException(status_code=400, detail=err.message)

    if config.app.environment == ENVIRONMENT.DEVELOPMENT:
        logger.info("OTP Code for %s: %s", email, otp_code)
    else:
        _, err = await resend_service.send_otp(
            to=email,
            _from=f"noreply@{config.resend.default_sender_email}",
            otp_code=otp_code,
        )
        if err:
            logger.error("Error sending OTP: %s", err)
            raise HTTPException(status_code=500, detail="Failed to send OTP.")
    return token
