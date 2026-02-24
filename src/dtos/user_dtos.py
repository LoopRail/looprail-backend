import re
from datetime import date
from typing import List, Optional

from pydantic import EmailStr, Field, field_validator
from pydantic_extra_types.country import CountryShortName

from src.dtos.base import Base
from src.types.common_types import PhoneNumber, RefreshTokenId, UserId
from src.types.error import error
from src.types.types import Gender, KYCStatus
from src.utils.app_utils import is_valid_email
from src.utils.auth_utils import validate_password_strength

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{4,16}$")


class SetTransactionPinRequest(Base):
    transaction_pin: str = Field(pattern=r"^\d{4}$")


class CompleteOnboardingRequest(Base):
    allow_notifications: bool
    fcm_token: Optional[str] = None
    questioner: list[str]


class UserCreate(Base):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    username: str = Field(min_length=4, max_length=16)
    country_code: CountryShortName
    gender: Gender
    phone_number: PhoneNumber

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_REGEX.fullmatch(v):
            raise ValueError(
                "Username must be 4–16 characters and contain only letters, numbers, '_' or '-'"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        err = validate_password_strength(v)
        if err:
            raise err
        return v

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        config: List[str] = cls.dto_config.get("disposable_email_domains", None)
        if config is None:
            raise error("Config not set")
        if not is_valid_email(v, config):
            raise error("Invalid email address")
        return v


class UserProfilePublic(Base):
    kyc_status: KYCStatus
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: CountryShortName
    phone_number: PhoneNumber
    date_of_birth: Optional[date] = None


class UserPublic(Base):
    id: UserId
    email: EmailStr
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    username: str
    gender: Gender
    is_email_verified: bool
    has_completed_onboarding: bool
    profile: Optional[UserProfilePublic] = None
    wallets: Optional[List[dict]] = None # Uses dict to avoid circular importing WalletWithAssets, avoiding cyclic graph


class UserProfileCreate(Base):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: CountryShortName
    phone_number: PhoneNumber
    date_of_birth: Optional[date] = None


class LoginRequest(Base):
    email: EmailStr
    password: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class RefreshTokenRequest(Base):
    refresh_token: RefreshTokenId
