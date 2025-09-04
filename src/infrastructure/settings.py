import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils import return_base_dir

env_dir = os.path.join(return_base_dir(), "config", ".env.dev")


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_dir, env_file_encoding="utf-8", extra="ignore"
    )


class BlockRaderConfig(ServerConfig):
    blockrader_api_key: str
    evm_master_wallet: str


class DatabaseConfig(ServerConfig):
    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str

    def get_uri(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


block_rader_config = BlockRaderConfig()
database_config = DatabaseConfig()