from __future__ import annotations
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Tuple, Type, TypeVar

from jose import JWTError, jwt

from src.types import Error, error

if TYPE_CHECKING:
    from src.infrastructure.settings import JWTConfig
    from src.types.access_token_types import AccessToken

T = TypeVar("T", bound="AccessToken")


class JWTUsecase:
    def __init__(self, jwt_config: JWTConfig):
        self.jwt_config = jwt_config

    def create_access_token(self, data: AccessToken, exp_minutes: int) -> str:
        """
        Create a JWT from a AccessToken object with a given expiration in minutes.
        """
        to_encode = data.model_dump()

        expire = datetime.utcnow() + timedelta(minutes=exp_minutes)
        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            self.jwt_config.secret_key,
        )
        return encoded_jwt

    def verify_access_token(
        self, token: str, response_model: Type[T]
    ) -> Tuple[Optional[T], Error]:
        """
        Decode and validate a JWT, returning a typed response model and any error.
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_config.secret_key,
                algorithms=[self.jwt_config.algorithm],
                options={
                    "require_sub": True,
                    "require_exp": True,
                },
            )
        except JWTError as e:
            return None, error(f"Could not decode JWT: {e}")

        return response_model(**payload), None
