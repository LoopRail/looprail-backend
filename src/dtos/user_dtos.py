from datetime import date
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import EmailStr, Field, field_validator, model_validator

from src.dtos.base import Base
from src.infrastructure import config
from src.types import Gender, KYCStatus, error
from src.utils import (get_country_info, is_valid_country_code,
                       validate_and_format_phone_number,
                       validate_password_strength)


class OnboardUserUpdate(Base):
    transaction_pin: list[int]
    allow_notificatiosn: bool
    questioner: list[str]


class PhoneNumber(Base):
    code: str
    number: str
    country_code: str

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        if not is_valid_country_code(config.countries, v):
            raise error(f"Country code '{v}' is not supported")
        return v.upper()

    @model_validator(mode="after")
    def check_dial_code(self) -> "PhoneNumber":
        country_info = get_country_info(config.countries, self.country_code)
        if country_info and country_info.dial_code != self.code:
            raise error(
                f"Dial code '{self.code}' does not match country '{self.country_code}'"
            )
        return self

    @model_validator(mode="after")
    def validate_and_format_number(self) -> "PhoneNumber":
        self.number = validate_and_format_phone_number(self.number, self.country_code)
        return self


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
    phone_number: str
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
    phone_number: str
    date_of_birth: date
    user_id: UUID


class LoginRequest(Base):
    email: EmailStr
    password: str


class RefreshTokenRequest(Base):
    refresh_token: str
