from enum import Enum


class SupportedCurrencies(str, Enum):
    NGN = "ngn"
    USD = "usd"


class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionMethod(str, Enum):
    CARD = "card"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"
    WALLET_TRANSFER = "wallet_transfer"


class Chain(str, Enum):
    POLYGON = "polygon"
    BASE = "base"
    ETHEREUM = "ethereum"
    BITCOIN = "btc"


class KYCStatus(str, Enum):
    """Represents the KYC status of a user."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
