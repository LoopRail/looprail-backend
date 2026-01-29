import json
import os
from typing import List

import toml

from src.infrastructure.logger import get_logger
from src.infrastructure.security import Argon2Config
from src.infrastructure.settings import (ENVIRONMENT, AppSettings,
                                         BlockRaderConfig, DatabaseConfig,
                                         JWTConfig, LedgderServiceConfig,
                                         OTPConfig, PayCrestConfig,
                                         PaystackConfig, RedisConfig,
                                         ResendConfig)
from src.types.country_types import CountriesData
from src.types.ledger_types import LedgerConfig
from src.types.types import WalletConfig
from src.utils import return_base_dir

logger = get_logger(__name__)


def load_wallet_configs_into_config(
    environment: ENVIRONMENT,
) -> WalletConfig | None:
    logger.debug("Entering load_wallet_configs_into_config function.")
    config_filename = (
        "blockrader.json"
        if environment in (ENVIRONMENT.DEVELOPMENT, ENVIRONMENT.STAGING)
        else "blockrader.prod.json"
    )
    logger.debug("Determined wallet config filename: %s", config_filename)

    config_path = os.path.join(return_base_dir(), "config", config_filename)
    logger.debug("Wallet config file path: %s", config_path)

    try:
        logger.debug("Attempting to open wallet config file: %s", config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            logger.debug("File opened. Attempting to parse JSON.")
            raw_config = json.load(f)
            logger.debug("JSON parsed successfully.")
            logger.debug("raw_config type: %s", type(raw_config))

        wallet_config = WalletConfig(wallets=raw_config["wallets"])
        logger.info("Successfully loaded wallet configs from %s", config_path)
        return wallet_config

    except FileNotFoundError:
        logger.warning("Config file not found: %s", config_path)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in config file: %s", config_path)
    except Exception as e:
        logger.error("An unexpected error occurred while loading wallet configs: %s", e)
    logger.debug("Exiting load_wallet_configs_into_config function with None.")
    return None


def load_countries() -> CountriesData:
    logger.debug("Entering load_countries function.")
    config_path = os.path.join(return_base_dir(), "config", "countires.json")
    logger.debug("Countries config file path: %s", config_path)
    try:
        logger.debug("Attempting to open countries config file: %s", config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            logger.debug("File opened. Attempting to parse JSON.")
            data = json.load(f)
            logger.debug("JSON parsed successfully.")
            logger.info("Successfully loaded countries data from %s", config_path)
            return CountriesData(**data)
    except FileNotFoundError:
        logger.warning("Countries config file not found: %s", config_path)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in countries config file: %s", config_path)
    except Exception as e:
        logger.error("An unexpected error occurred while loading countries data: %s", e)
    logger.debug("Exiting load_countries function with empty CountriesData.")
    return CountriesData(countries={})


def load_disposable_email_domains() -> List[str]:
    logger.debug("Entering load_disposable_email_domains function.")
    config_path = os.path.join(
        return_base_dir(), "config", "disposable_email_domains.txt"
    )
    logger.debug("Disposable email domains config file path: %s", config_path)
    try:
        logger.debug(
            "Attempting to open disposable email domains config file: %s", config_path
        )
        with open(config_path, "r", encoding="utf-8") as f:
            domains = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
            logger.info(
                "Successfully loaded %s disposable email domains from %s",
                len(domains),
                config_path,
            )
            return domains
    except FileNotFoundError:
        logger.warning(
            "Disposable email domains config file not found: %s", config_path
        )
    except Exception as e:
        logger.error(
            "An unexpected error occurred while loading disposable email domains: %s", e
        )
    logger.debug("Exiting load_disposable_email_domains function with empty list.")
    return []


def load_ledger_settings_from_file(environment: ENVIRONMENT) -> LedgerConfig:
    logger.debug("Entering load_ledger_settings_from_file function.")
    config_filename = (
        "ledger_config.toml"
        if environment == ENVIRONMENT.DEVELOPMENT
        else f"ledger_config.{environment.value}.toml"
    )
    logger.debug("Determined ledger config filename: %s", config_filename)
    config_path = os.path.join(return_base_dir(), "config", config_filename)
    logger.debug("Ledger config file path: %s", config_path)
    try:
        logger.debug("Attempting to open ledger config file: %s", config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            logger.debug("File opened. Attempting to parse TOML.")
            raw_configs = toml.load(f)
            logger.debug("TOML parsed successfully.")
        logger.info("Successfully loaded ledger settings from %s", config_path)
        return LedgerConfig(**raw_configs)
    except FileNotFoundError:
        logger.warning("Ledger config file not found: %s", config_path)
    except toml.TomlDecodeError:
        logger.warning("Invalid TOML in ledger config file: %s", config_path)
    except Exception as e:
        logger.error(
            "An unexpected error occurred while loading ledger settings: %s", e
        )
    logger.debug(
        "Exiting load_ledger_settings_from_file function with empty LedgerConfig."
    )
    return LedgerConfig(ledgers=[])


class Config:
    def __init__(self):
        logger.debug("Initializing Config class.")
        self.app: AppSettings = AppSettings()
        logger.debug("Application environment set to: %s", self.app.environment.value)
        self.jwt: JWTConfig = JWTConfig()
        self.otp: OTPConfig = OTPConfig()
        self.resend: ResendConfig = ResendConfig()
        self.block_rader: BlockRaderConfig = BlockRaderConfig()
        self.ledger: LedgderServiceConfig = LedgderServiceConfig()
        self.paycrest: PayCrestConfig = PayCrestConfig()
        self.paystack: PaystackConfig = PaystackConfig()
        self.database: DatabaseConfig = DatabaseConfig()
        self.redis: RedisConfig = RedisConfig()
        self.argon2: Argon2Config = Argon2Config()
        self.countries: CountriesData = load_countries()
        logger.debug("Countries data loaded.")

        self.disposable_email_domains: List[str] = load_disposable_email_domains()
        logger.debug("Disposable email domains loaded.")
        self.ledger.ledgers: LedgerConfig = load_ledger_settings_from_file(
            self.app.environment
        )
        logger.debug("Ledger settings loaded.")
        self.block_rader.wallets: WalletConfig | None = load_wallet_configs_into_config(
            self.app.environment
        )
        logger.debug("BlockRader wallet configs loaded.")

        if self.app.environment == ENVIRONMENT.PRODUCTION:
            self.resend.default_sender_domain = "looprail.xyz"
        elif self.app.environment == ENVIRONMENT.STAGING:
            self.resend.default_sender_domain = "staging.looprail.xyz"
        else:
            self.resend.default_sender_domain = None
        logger.debug(
            "Resend default sender domain set to: %s", self.resend.default_sender_domain
        )
        logger.debug("Config class initialization complete.")


def load_config() -> Config:
    config_obj = Config()

    logger.debug("Config loaded with ENVIRONMENT: %s", config_obj.app.environment)
    logger.debug("Database driver: %s", config_obj.database.db_driver)
    logger.debug("Database URI: %s", config_obj.database.get_uri())
    return config_obj
