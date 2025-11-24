import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils import return_base_dir

if os.getenv("TESTING") == "true":
    env_dir = os.path.join(return_base_dir(), "config", ".env.test")
else:
    env_dir = os.path.join(return_base_dir(), "config", ".env.dev")

USDC_ADDRESS = "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
ONBOARDING_TOKEN_EXP_MINS = 10
USDC_ABI = [
    {
        "name": "transfer",
        "type": "function",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
    }
]


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_dir, env_file_encoding="utf-8", extra="ignore"
    )


class JWTConfig(ServerConfig):
    algorithm: str
    secret_key: str


class OTPConfig(ServerConfig):
    hmac_secret: str
    otp_length: int
    otp_expire_seconds: str
    otp_max_attempts: str


class ResendConfig(ServerConfig):
    resend_api_key: str


class BlockRaderConfig(ServerConfig):
    blockrader_api_key: str
    base_usdc_asset_id_master: str
    base_master_wallet: str
    base_master_wallet_id: str  # TEMP


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


block_rader_config = BlockRaderConfig()
paycrest_config = PayCrestConfig()
database_config = DatabaseConfig()
paystack_config = PaystackConfig()
redis_config = RedisConfig()
otp_config = OTPConfig()
resend_config = ResendConfig()
jwt_config = JWTConfig()


# TODO  we will need to create a separate config for wallets soon
# Starting with base because of blockrader's quota
# Pobably enter them from an admin ui since we already have a provider model
