import json
import os
from typing import List

import toml
import yaml

from src.infrastructure.logger import get_logger
from src.infrastructure.settings import (AppSettings, BlockRaderConfig,
                                         DatabaseConfig, JWTConfig, OTPConfig,
                                         PayCrestConfig, PaystackConfig,
                                         RedisConfig, ResendConfig,
                                         WalletConfig)
from src.infrastructure.security import Argon2Config
from src.types import CountriesData, LedgerSettings
from src.utils import return_base_dir
logger = get_logger(__name__)


def load_wallet_configs_into_config(config: BlockRaderConfig):
    config_path = os.path.join(return_base_dir(), "config", "blockrader.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_configs = yaml.safe_load(f)
        config.wallets = [WalletConfig(**c) for c in raw_configs]
    except FileNotFoundError:
        config.wallets = []


def load_countries() -> CountriesData:
    config_path = os.path.join(return_base_dir(), "config", "countires.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.debug("Loaded %s", config_path)
            return CountriesData(**data)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.debug("Could not load %s", config_path)
        return CountriesData(countries={})


def load_disposable_email_domains() -> List[str]:
    config_path = os.path.join(
        return_base_dir(), "config", "disposable_email_domains.txt"
    )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            logger.debug("Loaded %s", config_path)
            return [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        logger.debug("Could not load %s", config_path)
        return []


def load_ledger_settings_from_file() -> LedgerSettings:
    config_path = os.path.join(return_base_dir(), "config", "ledger_config.toml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_configs = toml.load(f)
        logger.debug("Loaded %s", config_path)
        return LedgerSettings(**raw_configs)
    except FileNotFoundError:
        logger.debug("Could not load %s", config_path)
        return LedgerSettings(ledgers=[])
    except Exception as e:
        logger.error("Error loading ledger config: %s", e)
        return LedgerSettings(ledgers=[])


class Config:
    def __init__(self):
        self.app: AppSettings = AppSettings()
        self.jwt: JWTConfig = JWTConfig()
        self.otp: OTPConfig = OTPConfig()
        self.resend: ResendConfig = ResendConfig()
        self.block_rader: BlockRaderConfig = BlockRaderConfig()
        self.paycrest: PayCrestConfig = PayCrestConfig()
        self.paystack: PaystackConfig = PaystackConfig()
        self.database: DatabaseConfig = DatabaseConfig()
        self.redis: RedisConfig = RedisConfig()
        self.argon2: Argon2Config = Argon2Config()
        self.countries: CountriesData = load_countries()
        self.disposable_email_domains: List[str] = load_disposable_email_domains()
        self.ledger: LedgerSettings = load_ledger_settings_from_file()

        load_wallet_configs_into_config(self.block_rader)


def load_config() -> Config:
    return Config()


config = load_config()
