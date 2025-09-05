from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr

from src.types import KYCStatus


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    first_name: str
    last_name: str


class UserPublic(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    first_name: str
    last_name: str

    class Config:
        from_attributes = True


class UserProfileCreate(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone_number: str
    date_of_birth: date


class UserProfilePublic(BaseModel):
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