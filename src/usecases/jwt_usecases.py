from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Tuple, Type, TypeVar
from uuid import uuid4

from jose import JWTError, jwt

from src.infrastructure.settings import JWTConfig
from src.types import Error, error
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from src.types.access_token_types import Token

T = TypeVar("T", bound="Token")


class JWTUsecase:
    def __init__(self, config: JWTConfig):
        self.config = config
        logger.debug("JWTUsecase initialized.")

    def create_token(self, data: Token, exp_minutes: int) -> str:
        """
        Create a JWT from a Token object with a given expiration in minutes.
        """
        logger.debug(
            "Creating token for subject: %s with expiration: %s minutes",
            data.sub,
            exp_minutes,
        )
        to_encode = data.model_dump()

        expire = datetime.utcnow() + timedelta(minutes=exp_minutes)
        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )
        logger.info("Token created successfully for subject: %s", data.sub)
        return encoded_jwt

    def verify_token(
        self, token: str, response_model: Type[T]
    ) -> Tuple[Optional[T], Error]:
        """
        Decode and validate a JWT, returning a typed response model and any error.
        """
        logger.debug("Verifying token with response model: %s", response_model.__name__)
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
            logger.debug("Token successfully decoded.")
        except JWTError as e:
            logger.error("Failed to decode JWT: %s", e)
            return None, error(f"Could not decode JWT: {e}")

        return response_model(**payload), None

    def create_refresh_token(self) -> str:
        """
        Generates a random string for a refresh token.
        """
        refresh_token = str(uuid4())
        logger.debug("Generated new refresh token.")
        return refresh_token
