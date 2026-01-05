import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.infrastructure.constants import (
    ACCESS_TOKEN_EXP_MINS,
    ONBOARDING_TOKEN_EXP_MINS,
    REFRESH_TOKEN_EXP_DAYS,
    ARGON2_TIME_COST,
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_HASH_LEN,
    ARGON2_SALT_LEN,
)
from src.infrastructure.security import Argon2Config
from src.types.types import WalletConfig
from src.utils import return_base_dir


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file_encoding="utf-8")

    testing: bool = Field(False, alias="TESTING")
    env_file: str = ".env.dev"

    @property
    def get_env_file_path(self) -> str:
        env_file = ".env.dev" if self.testing else self.env_file
        return os.path.join(return_base_dir(), "config", env_file)


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=AppSettings().get_env_file_path,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class JWTConfig(ServerConfig):
    algorithm: str
    secret_key: str
    access_token_expire_minutes: int = ACCESS_TOKEN_EXP_MINS
    onboarding_token_expire_minutes: int = ONBOARDING_TOKEN_EXP_MINS
    refresh_token_expires_in_days: int = REFRESH_TOKEN_EXP_DAYS


class OTPConfig(ServerConfig):
    hmac_secret: str
    otp_length: int
    otp_expire_seconds: str
    otp_max_attempts: str


class ResendConfig(ServerConfig):
    resend_api_key: str


class BlockRaderConfig(ServerConfig):
    blockrader_api_key: str
    wallets: List[WalletConfig] = []


class PayCrestConfig(ServerConfig):
    paycrest_api_key: str
    paycrest_api_secret: str


class PaystackConfig(ServerConfig):
    paystack_api_key: str


class DatabaseConfig(ServerConfig):
    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str

    def get_uri(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class RedisConfig(ServerConfig):
    redis_port: int
    redis_host: str
    redis_username: str | None = None
    redis_password: str | None = None
