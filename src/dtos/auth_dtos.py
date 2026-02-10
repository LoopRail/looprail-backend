from typing import Optional

from pydantic import Field

from src.dtos.base import Base
from src.dtos.user_dtos import UserPublic
from src.dtos.wallet_dtos import AuthorizationDetails
from src.types.common_types import DeviceID


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
    authorization: AuthorizationDetails


class BiometricEnrollRequest(Base):
    public_key: str
    device_id: DeviceID


class BiometricLoginRequest(Base):
    challenge_id: str
    code_verifier: str
    public_key: str
    signature: str
    device_id: DeviceID
