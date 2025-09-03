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


block_rader_config = BlockRaderConfig()
