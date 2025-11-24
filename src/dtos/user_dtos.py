from datetime import date
from enum import StrEnum
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import EmailStr, Field, field_validator

from src.dtos.base import Base
from src.types import KYCStatus, error


class Gender(StrEnum):
    MALE = "male"
    FEMAIL = "FEMALE"


class OnboardUserUpdate(Base):
    first_name: str
    last_name: str
    gender: Gender


class UserCreate(Base):
    email: EmailStr
    country: str
    country_code: str
    phone_number: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, val: any):
        try:
            email = validate_email(val, check_deliverability=True)

            return email.email

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
