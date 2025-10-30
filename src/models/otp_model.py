from time import time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from src.infrastructure.logger import get_logger
from src.types import OtpStatus, OtpType, error
from src.utils import kebab_case

logger = get_logger(__name__)


class Otp(BaseModel):
    model_config = ConfigDict(alias_generator=kebab_case)
    user_email: EmailStr
    created_at: int = Field(default_factory=lambda: int(time.time()))
    expires_at: int = Field(default_factory=lambda: int(time.time()) + 60)  # seconds
    status: OtpStatus = OtpStatus.ACTIVE
    code_hash: str = Field(alias="hash")
    otp_type: OtpType = Field(alias="type", default=OtpType.EMAIL_VERIFICATION)
    attempts: int = 0

    def is_expired(self) -> bool:
        """Checks if the OTP has expired."""
        return time.time() > self.expires_at

    @model_validator(mode="after")
    def validate_otp(self) -> "Otp":
        """
        Validates the OTP.

        An OTP is considered invalid if the number of verification attempts
        exceeds 3 or if its status is not 'active'.
        """
        if self.is_expired():
            logger.error("OTP has expired")
            raise error("Invalid OTP")
        if self.attempts > 3:
            logger.error("OTP has been attempted too many times.")
            raise error("Invalid OTP")
        if self.status != OtpStatus.ACTIVE:
            logger.error("OTP is not active.")
            raise error("Invalid OTP")
        return self
