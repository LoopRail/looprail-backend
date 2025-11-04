from pydantic import EmailStr

from src.dtos.base import Base
from src.types import OtpType


class OtpCreate(Base):
    email: EmailStr


class VerifyOtpRequest(Base):
    code: str
    otp_type: OtpType = OtpType.EMAIL_VERIFICATION
