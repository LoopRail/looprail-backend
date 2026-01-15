import time

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.infrastructure.logger import get_logger
from src.types.types import OtpStatus, OtpType
from src.utils import kebab_case

logger = get_logger(__name__)


class Otp(BaseModel):
    """
    Represents a one-time password (OTP) instance for verification purposes.
    """

    __id_prefix__ = "otp_"
    model_config = ConfigDict(
        alias_generator=kebab_case, populate_by_name=True, use_enum_values=True
    )

    user_email: EmailStr
    created_at: int = Field(default_factory=lambda: int(time.time()))
    expires_at: int = Field(
        default_factory=lambda: int(time.time()) + 300
    )  # expires in 5 minutes
    status: OtpStatus = OtpStatus.ACTIVE
    code_hash: str = Field(alias="hash")
    otp_type: OtpType = Field(
        alias="type", default=OtpType.ONBOARDING_EMAIL_VERIFICATION
    )
    attempts: int = 0

    def is_expired(self) -> bool:
        """Check if the OTP has expired."""
        return time.time() > self.expires_at

    # @model_validator(mode="after")
    # def validate_otp(self) -> "Otp":
    #     """
    #     Validates the OTP instance after initialization.
    #     """
    #     if self.is_expired():
    #         logger.error("OTP has expired")
    #         raise error("Invalid OTP")
    #     if self.attempts > 3:
    #         logger.error("OTP has been attempted too many times.")
    #         raise error("Invalid OTP")
    #     if self.status != OtpStatus.ACTIVE:
    #         logger.error("OTP is not active.")
    #         raise error("Invalid OTP")
    #     return self
