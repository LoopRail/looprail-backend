from pydantic import Field
from src.dtos.user_dtos import UserPublic
from src.dtos.base import Base


class MessageResponse(Base):
    message: str


class AuthTokensResponse(Base):
    access_token: str
    refresh_token: str


class AuthWithTokensAndUserResponse(MessageResponse, AuthTokensResponse):
    user: UserPublic


class CreateUserResponse(Base):
    user: UserPublic
    otp_token: str


class ChallengeResponse(Base):
    challenge_id: str
    nonce: str


class PasscodeSetRequest(Base):
    passcode: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class PasscodeLoginRequest(Base):
    challenge_id: str
    code_verifier: str
    passcode: str = Field(..., pattern=r"^\d{6}$")


class BiometricEnrollRequest(Base):
    public_key: str
    device_id: str


class BiometricLoginRequest(Base):
    challenge_id: str
    code_verifier: str
    public_key: str
    signature: str
    device_id: str
