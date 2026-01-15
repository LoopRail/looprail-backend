from enum import StrEnum
from typing import List, Optional, Tuple

from pydantic import BaseModel

from src.types.blockrader.types import AssetData
from src.types.common_types import Chain
from src.types.error import Error, error


class Wallet(BaseModel):
    chain: Chain
    wallet_id: str
    wallet_name: str
    wallet_address: str
    active: bool
    assets: List[AssetData]


class WalletConfig(BaseModel):
    wallets: List[Wallet]

    def get_wallet(self, wallet_name: str) -> Tuple[Optional[Wallet], Error]:
        for wallet in self.wallets:
            if wallet.wallet_name == wallet_name:
                return wallet, None
        return None, error(f"Wallet with name {wallet_name} not found")


class TransactionStatus(StrEnum):
    COMPLETED = "completed"
    PENDING = "pending"
    FAILED = "failed"


class Currency(StrEnum):
    NAIRA = "ngn"


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


class TransactionType(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class PaymentType(StrEnum):
    FIAT = "fiat"
    CRYPTO = "crypto"


class PaymentMethod(StrEnum):
    CARD = "card"
    APPLE_PAY = "apple-pay"
    GOOGLE_PAY = "google_pay"
    BANK_TRANSFER = "bank-transfer"
    MOBILE_MONEY = "mobile-money"
    WALLET_TRANSFER = "wallet-transfer"


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


class InstitutionCountry(StrEnum):
    NG = "NG"
    KY = "KY"


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class WithdrawalMethod(StrEnum):
    BANK_TRANSFER = "withdraw:bank-transfer"
    EXTERNAL_WALLET = "withdraw:external-wallet"
