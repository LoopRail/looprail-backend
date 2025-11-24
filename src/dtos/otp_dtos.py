from email_validator import EmailNotValidError, validate_email
from pydantic import EmailStr, field_validator

from src.dtos.base import Base
from src.types import OtpType, error


class OtpCreate(Base):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, val: any):
        try:
            email = validate_email(val, check_deliverability=True)

            return email.email

        except EmailNotValidError as e:
            raise error("Invalid email address") from e


class VerifyOtpRequest(Base):
    code: str
    otp_type: OtpType = OtpType.ONBOARDING_EMAIL_VERIFICATION


class OTPSuccessResponse(Base):
    message: str
    access_token: str
