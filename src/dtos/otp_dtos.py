from typing import List

from pydantic import EmailStr, field_validator

from src.dtos.base import Base
from src.types.error import error
from src.types.types import OtpType
from src.utils.app_utils import is_valid_email


class OtpCreate(Base):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        config: List[str] = cls.dto_config.get("disposable_email_domains", None)
        if config is None:
            raise error("Config not set")
        if not is_valid_email(v, config):
            raise error("Invalid email address")
        return v


class VerifyOtpRequest(Base):
    code: str
    otp_type: OtpType = OtpType.ONBOARDING_EMAIL_VERIFICATION


class OTPSuccessResponse(Base):
    message: str
    access_token: str
