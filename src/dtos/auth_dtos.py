from typing import Optional

from pydantic import Field, field_validator

from src.dtos.base import Base
from src.dtos.user_dtos import UserPublic
from src.types.common_types import DeviceID
from src.utils.auth_utils import validate_password_strength


class MessageResponse(Base):
    message: str


class AuthTokensResponse(Base):
    access_token: str
    refresh_token: str | None = None


class AuthWithTokensAndUserResponse(MessageResponse):
    session_id: str | None = None
    access_token: str | None = Field(None, alias="access-token")
    refresh_token: str | None = Field(None, alias="refresh-token")
    user: UserPublic


class CreateUserResponse(Base):
    user: UserPublic
    otp_token: str


class ChallengeResponse(Base):
    challenge_id: str
    nonce: str


class PasscodeSetRequest(Base):
    passcode: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class PasscodeLoginRequest(Base):
    challenge_id: str
    code_verifier: str
    passcode: str = Field(..., pattern=r"^\d{6}$")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class BiometricEnrollRequest(Base):
    public_key: str
    device_id: DeviceID


class BiometricLoginRequest(Base):
    challenge_id: str
    code_verifier: str
    public_key: str
    signature: str
    device_id: DeviceID


class PasswordResetRequest(Base):
    email: str


class PasswordResetVerifyRequest(Base):
    code: str


class PasswordResetVerifyResponse(Base):
    message: str
    reset_token: str


class PasswordResetConfirmRequest(Base):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        err = validate_password_strength(v)
        if err:
            raise err
        return v


class PasswordResetResponse(Base):
    message: str
    otp_token: str | None = None
