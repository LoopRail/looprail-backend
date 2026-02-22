from enum import StrEnum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, RootModel

from src.types.blockrader.types import AssetData
from src.types.common_types import Chain
from src.types.error import Error, error


class Bank(BaseModel):
    name: str
    code: Optional[str] = None
    type: Optional[str] = None
    logo: Optional[str] = None
    id: Optional[str] = None


class BanksData(RootModel[Dict[str, List[Bank]]]):
    def get(self, country_code: Optional[str] = None, **kwargs: Any) -> List[Bank]:
        """
        Retrieves a list of banks based on optional country code and other criteria.
        If country_code is None, searches across all countries.
        """
        found_banks = []
        target_countries = []

        if country_code:
            target_countries.append(country_code.upper())
        else:
            target_countries.extend(self.root.keys())

        for c_code in target_countries:
            banks_in_country = self.root.get(c_code, [])
            for bank in banks_in_country:
                match = True
                for key, value in kwargs.items():
                    if not hasattr(bank, key) or getattr(bank, key) != value:
                        match = False
                        break
                if match:
                    found_banks.append(bank)
        return found_banks


class Wallet(BaseModel):
    chain: Chain
    wallet_id: str
    wallet_name: str
    wallet_address: str
    active: bool
    assets: List[AssetData]

    def get(self, **kwargs: Any) -> Tuple[Optional[AssetData], Error]:
        if not kwargs:
            return None, error("No search criteria provided")

        for asset in self.assets:
            match = all(
                getattr(asset, key, None) == value for key, value in kwargs.items()
            )
            if match:
                return asset, None

        criteria = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        return None, error(f"Asset matching criteria ({criteria}) not found")


class WalletConfig(BaseModel):
    wallets: List[Wallet]

    def get_wallet(self, **kwargs: Any) -> Tuple[Optional[Wallet], Error]:
        if not kwargs:
            return None, error("No search criteria provided")

        for wallet in self.wallets:
            match = all(
                getattr(wallet, key, None) == value for key, value in kwargs.items()
            )
            if match:
                return wallet, None

        criteria = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        return None, error(f"Wallet matching criteria ({criteria}) not found")


class TransactionStatus(StrEnum):
    COMPLETED = "completed"
    PENDING = "pending"
    FAILED = "failed"


class Currency(StrEnum):
    NAIRA = "ngn"
    US_Dollar = "usd"


class AssetType(StrEnum):
    USDC = "usdc"
    USDT = "usdt"
    cNGN = "cngn"


class TokenStandard(StrEnum):
    ERC20 = "erc20"
    BEP20 = "bep20"
    TRC20 = "trc20"


class Provider(StrEnum):
    BLOCKRADER = "blockrader"


# Add to your existing TransactionType enum
class TransactionType(StrEnum):
    # Existing crypto types
    CRYPTO_SEND = "crypto:send"
    CRYPTO_RECEIVE = "crypto:receive"
    CRYPTO_SWAP = "crypto:swap"

    # New bank/fiat types
    BANK_WITHDRAWAL = "withdraw:bank-transfer"
    BANK_DEPOSIT = "deposit:bank"
    CARD_DEPOSIT = "deposit:card"

    # Internal transfers
    INTERNAL_TRANSFER = "transfer:internal"

    # Other
    FEE = "fee"
    REFUND = "refund"

    # Payment types
    DEBIT = "debit"
    CREDIT = "credit"


class PaymentMethod(StrEnum):
    BLOCKCHAIN = "blockchain"
    BANK_TRANSFER = "bank-transfer"
    CARD = "card"
    INTERNAL = "internal"
    WALLET = "wallet"


class KYCStatus(StrEnum):
    """Represents the KYC status of a user."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class OtpType(StrEnum):
    ONBOARDING_EMAIL_VERIFICATION = "onboarding_email_verification"


class OtpStatus(StrEnum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    ATTEMPT_EXCEEDED = "attempt_exceeded"


class TokenType(StrEnum):
    ONBOARDING_TOKEN = "onboarding-token"
    ACCESS_TOKEN = "access-token"
    REFRESH_TOKEN = "refresh-token"


class Platform(StrEnum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class InstitutionCountry(StrEnum):
    NG = "NG"
    KY = "KY"


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class WithdrawalMethod(StrEnum):
    BANK_TRANSFER = "withdraw:bank-transfer"
    EXTERNAL_WALLET = "withdraw:external-wallet"
