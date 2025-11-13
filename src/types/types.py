from enum import Enum


class TransactionStatus(str, Enum):
    COMPLETED = "completed"
    PENDING = "pending"
    FAILED = "failed"


class SupportedCurrency(str, Enum):
    NAIRA = "ngn"


class Assets(str, Enum):
    USDC = "usdc"
    USDT = "usdt"
    cNGN = "cngn"


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


class Chain(str, Enum):
    POLYGON = "polygon"
    BASE = "base"
    ETHEREUM = "ethereum"
    BITCOIN = "btc"


class SupportedNetworksRPC:
    BASE = "mainnet"
    BASE_SEPOLIA = "base_sepoila"


class KYCStatus(str, Enum):
    """Represents the KYC status of a user."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class OtpType(str, Enum):
    EMAIL_VERIFICATION = "email_verification"


class OtpStatus(str, Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    ATTEMPT_EXCEEDED = "attempt_exceeded"


class AccessToken(str, Enum):
    ONBOARDING_TOKEN = "onboarding_token"
