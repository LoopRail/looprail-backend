import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils import return_base_dir

env_dir = os.path.join(return_base_dir(), "config", ".env.dev")

USDC_ADDRESS = "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
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


class BlockRaderConfig(ServerConfig):
    blockrader_api_key: str
    evm_master_wallet: str
    base_usdc_asset_id: str
    base_wallet_id: str


class PayCrestConfig(ServerConfig):
    paycrest_base_url: str
    paycrest_api_key: str


class DatabaseConfig(ServerConfig):
    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str

    def get_uri(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


block_rader_config = BlockRaderConfig()
paycrest_config = PayCrestConfig()
database_config = DatabaseConfig()
