from datetime import date
from uuid import UUID

from pydantic import EmailStr

from src.types import KYCStatus
from src.dtos.base import Base


class UserCreate(Base):
    username: str
    email: EmailStr
    first_name: str
    last_name: str


class UserPublic(Base):
    id: UUID
    username: str
    email: EmailStr
    first_name: str
    last_name: str

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True

