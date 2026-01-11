from enum import Enum
from typing import List

from pydantic import BaseModel

from src.types.blockrader.types import AssetData
from src.types.common_types import Chain


class WalletConfig(BaseModel):
    chain: Chain
    wallet_id: str
    wallet_address: str
    active: bool
    assets: List[AssetData]


class TransactionStatus(str, Enum):
    COMPLETED = "completed"
    PENDING = "pending"
    FAILED = "failed"


class Currency(str, Enum):
    NAIRA = "ngn"


class AssetType(str, Enum):
    USDC = "usdc"
    USDT = "usdt"
    cNGN = "cngn"


class TokenStandard(str, Enum):
    ERC20 = "erc20"
    BEP20 = "bep20"
    TRC20 = "trc20"


class Provider(str, Enum):
    BLOCKRADER = "blockrader"


class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class PaymentType(str, Enum):
    FIAT = "fiat"
    CRYPTO = "crypto"


class PaymentMethod(str, Enum):
    CARD = "card"
    APPLE_PAY = "apple-pay"
    GOOGLE_PAY = "google_pay"
    BANK_TRANSFER = "bank-transfer"
    MOBILE_MONEY = "mobile-money"
    WALLET_TRANSFER = "wallet-transfer"


class KYCStatus(str, Enum):
    """Represents the KYC status of a user."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class OtpType(str, Enum):
    ONBOARDING_EMAIL_VERIFICATION = "onboarding_email_verification"


class OtpStatus(str, Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    ATTEMPT_EXCEEDED = "attempt_exceeded"


class TokenType(str, Enum):
    ONBOARDING_TOKEN = "onboarding-token"
    ACCESS_TOKEN = "access-token"
    REFRESH_TOKEN = "refresh-token"


class Platform(str, Enum):
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"


class InstitutionCountry(str, Enum):
    NG = "NG"
    KY = "KY"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
