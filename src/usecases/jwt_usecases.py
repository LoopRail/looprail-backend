from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Tuple, Type, TypeVar
from uuid import uuid4

from jose import JWTError, jwt

from src.infrastructure.settings import JWTConfig
from src.types import Error, error

if TYPE_CHECKING:
    from src.types.access_token_types import Token

T = TypeVar("T", bound="Token")


class JWTUsecase:
    def __init__(self, config: JWTConfig):
        self.config = config

    def create_token(self, data: Token, exp_minutes: int) -> str:
        """
        Create a JWT from a Token object with a given expiration in minutes.
        """
        to_encode = data.model_dump()

        expire = datetime.utcnow() + timedelta(minutes=exp_minutes)
        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            self.config.secret_key,
            algorithms=[self.config.algorithm],
        )
        return encoded_jwt

    def verify_token(
        self, token: str, response_model: Type[T]
    ) -> Tuple[Optional[T], Error]:
        """
        Decode and validate a JWT, returning a typed response model and any error.
        """
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                options={
                    "require_sub": True,
                    "require_exp": True,
                },
            )
        except JWTError as e:
            return None, error(f"Could not decode JWT: {e}")

        return response_model(**payload), None

    def create_refresh_token(self) -> str:
        """
        Generates a random string for a refresh token.
        """
        return str(uuid4())
