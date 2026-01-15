import re
from datetime import date
from typing import List

from pydantic import EmailStr, Field, field_validator

from src.dtos.base import Base
from src.types.common_types import PhoneNumber, UserId, UserProfileId
from src.types.country_types import CountriesData
from src.types.error import error
from src.types.types import Gender, KYCStatus
from src.utils import is_valid_country_code, is_valid_email, validate_password_strength

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{4,16}$")


class OnboardUserUpdate(Base):
    transaction_pin: list[int] = Field(max_length=4, min_length=4)
    allow_notificatiosn: bool
    questioner: list[str]


class UserCreate(Base):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    username: str = Field(min_length=4, max_length=16)
    country_code: str
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

    @field_validator("country_code")
    @classmethod
    def _validate_country_code(cls, v: str) -> str:
        config: CountriesData = cls.dto_config.get("allowed_countries", None)
        if config is None:
            raise error("Config not set")
        if not is_valid_country_code(config, v):
            raise error(f"Country code '{v.upper()}' is not supported")
        return v.upper()

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        config: List[str] = cls.dto_config.get("disposable_email_domains", None)
        if config is None:
            raise error("Config not set")
        if not is_valid_email(v, config):
            raise error("Invalid email address")
        return v


class UserPublic(Base):
    id: UserId
    email: EmailStr
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)


class UserProfileCreate(Base):
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone_number: PhoneNumber
    date_of_birth: date


class UserProfilePublic(Base):
    id: UserProfileId
    kyc_status: KYCStatus
    is_email_verified: bool
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone_number: PhoneNumber
    date_of_birth: date
    user_id: UserId


class LoginRequest(Base):
    email: EmailStr
    password: str


class RefreshTokenRequest(Base):
    refresh_token: str
