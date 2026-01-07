from datetime import date
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import EmailStr, Field, field_validator 

from src.dtos.base import Base
from src.infrastructure import config
from src.types import Gender, KYCStatus, error, PhoneNumber
from src.utils import (
    is_valid_country_code,
    validate_password_strength,
)


class OnboardUserUpdate(Base):
    transaction_pin: list[int]
    allow_notificatiosn: bool
    questioner: list[str]


class UserCreate(Base):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    country_code: str
    gender: Gender
    phone_number: PhoneNumber

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        err = validate_password_strength(v)
        if err:
            raise err
        return v

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        if not is_valid_country_code(config.countries, v):
            raise error(f"Country code '{v.upper()}' is not supported")
        return v.upper()

    @field_validator("email")
    @classmethod
    def validate_email(cls, val: any):
        try:
            email_info = validate_email(val, check_deliverability=True)
            if email_info.domain in config.disposable_email_domains:
                raise error("Disposable email addresses are not allowed")
            return email_info.email

        except EmailNotValidError as e:
            raise error("Invalid email address") from e


class UserPublic(Base):
    id: UUID
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
    id: UUID
    kyc_status: KYCStatus
    is_email_verified: bool
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone_number: PhoneNumber
    date_of_birth: date
    user_id: UUID


class LoginRequest(Base):
    email: EmailStr
    password: str


class RefreshTokenRequest(Base):
    refresh_token: str
