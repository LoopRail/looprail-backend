from fastapi import Body, Depends, HTTPException

from src.api.dependencies import get_config
from src.dtos import OtpCreate, UserCreate
from src.infrastructure import PRODUCTION_DOMAIN, STAGING_DOMAIN, get_logger
from src.infrastructure.config_settings import Config
from src.infrastructure.services import ResendService
from src.infrastructure.settings import ENVIRONMENT
from src.usecases import OtpUseCase

logger = get_logger(__name__)


async def send_otp_internal(
    environment: ENVIRONMENT,
    *,
    email: str,
    otp_usecases: OtpUseCase,
    resend_service: ResendService,
) -> str:
    logger.info("Initiating internal OTP send for email: %s", email)
    _, err = await otp_usecases.get_user_token(user_email=email)
    if err and err != "Not found":
        raise HTTPException(status_code=500, detail="Server Error")

    err = await otp_usecases.delete_otp(user_email=email)
    if err and err != "Not found":
        raise HTTPException(status_code=500, detail="Server Error")

    otp_code, token, err = await otp_usecases.generate_otp(user_email=email)
    if err:
        raise HTTPException(status_code=400, detail=err.message)

    if environment == ENVIRONMENT.DEVELOPMENT:
        logger.info("OTP Code for %s: %s", email, otp_code)
    else:
        domain = (
            STAGING_DOMAIN if environment == ENVIRONMENT.STAGING else PRODUCTION_DOMAIN
        )
        _, err = await resend_service.send_otp(
            to=email,
            _from=f"noreply@{domain}",
            otp_code=otp_code,
        )
        if err:
            logger.error("Error sending OTP: %s", err)
            raise HTTPException(status_code=500, detail="Failed to send OTP.")
    return token

# TODO move to main

async def set_user_create_config(config: Config = Depends(get_config)):
    logger.debug("Entering set_user_create_config")
    config = {
        "disposable_email_domains": config.disposable_email_domains,
        "allowed_countries": config.countries,
    }
    UserCreate.dto_config = config


async def set_send_otp_config(config: Config = Depends(get_config)):
    logger.debug("Entering set_send_otp_config")
    config = {
        "disposable_email_domains": config.disposable_email_domains,
    }
    OtpCreate.dto_config = config
