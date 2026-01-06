from pydantic import BaseModel
from typing import Optional

from src.dtos import UserPublic
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