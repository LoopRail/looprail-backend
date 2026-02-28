import os
from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.infrastructure.constants import (
    ACCESS_TOKEN_EXP_MINS,
    ONBOARDING_TOKEN_EXP_MINS,
    REFRESH_TOKEN_EXP_DAYS,
)
from src.types.ledger_types import LedgerConfig
from src.types.types import WalletConfig
from src.utils.app_utils import return_base_dir


class ENVIRONMENT(str, Enum):
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"
    TEST = "test"


class EnvironmentSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file_encoding="utf-8")
    environment: ENVIRONMENT = Field(
        default=ENVIRONMENT.DEVELOPMENT,
        alias="ENVIRONMENT",
    )

    @property
    def get_env_file_path(self) -> str:
        filename = (
            ".env"
            if self.environment == ENVIRONMENT.DEVELOPMENT
            else f".env.{self.environment.value}"
        )
        return os.path.join(return_base_dir(), "config", filename)


# Bootstrap environment to find the correct .env file
_env_bootstrap = EnvironmentSettings()


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_bootstrap.get_env_file_path,
        env_file_encoding="utf-8",
        extra="ignore",
    )
    environment: ENVIRONMENT = Field(
        default=ENVIRONMENT.DEVELOPMENT,
        alias="ENVIRONMENT",
    )


class AppSettings(ServerConfig):
    logo_url: str | None = Field(default=None, alias="APP_LOGO_URL")
    full_logo_url: str | None = Field(default=None, alias="APP_FULL_LOGO_URL")
    icon_logo_url: str | None = Field(default=None, alias="APP_ICON_LOGO_URL")


class LedgderServiceConfig(ServerConfig):
    ledger_service_name: str
    ledger_service_host: str
    ledger_service_api_key: str
    ledgers: LedgerConfig | None = None


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
    default_sender_domain: str | None = None


class BlockRaderConfig(ServerConfig):
    blockrader_api_key: str
    wallets: WalletConfig | None = None


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
    database_uri: str | None = None
    db_driver: str = "postgresql+asyncpg"

    def get_uri(self) -> str:
        if self.database_uri:
            return self.database_uri
        return f"{self.db_driver}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class RedisConfig(ServerConfig):
    redis_port: int
    redis_host: str
    redis_username: str | None = None
    redis_password: str | None = None


class FirebaseConfig(ServerConfig):
    firebase_project_id: str | None = None
    firebase_private_key_id: str | None = Field(default=None, alias="FIREBASE_PRIVATE_KEY_id")
    firebase_client_id: str | None = None
    firebase_private_key: str | None = None
    firebase_client_email: str | None = None
    firebase_client_x509_cert_url: str | None = None
