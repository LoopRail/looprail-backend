from typing import List

from pydantic import EmailStr, field_validator
from pydantic_core.core_schema import FieldValidationInfo

from src.dtos.base import Base
from src.types.error import error
from src.types.types import OtpType
from src.utils import is_valid_email


class OtpCreate(Base):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str, info: FieldValidationInfo) -> str:
        config: List[str] = info.context["disposable_email_domains"]
        if not is_valid_email(config, v):
            raise error("Invalid email address")
        return v


class VerifyOtpRequest(Base):
    code: str
    otp_type: OtpType = OtpType.ONBOARDING_EMAIL_VERIFICATION


class OTPSuccessResponse(Base):
    message: str
    access_token: str
