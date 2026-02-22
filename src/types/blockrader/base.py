from enum import Enum

from pydantic import BaseModel, ConfigDict


class baseBlockRaderType(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="allow",
        arbitrary_types_allowed=True,
        use_enum_values=True,
    )


class baseResponse(baseBlockRaderType):
    message: str
    statusCode: int


class WebhookEventType(str, Enum):
    DEPOSIT_SUCCESS = "deposit.success"
    DEPOSIT_PROCESSING = "deposit.processing"
    DEPOSIT_FAILED = "deposit.failed"
    DEPOSIT_CANCELLED = "deposit.cancelled"
    DEPOSIT_SWEPT_SUCCESS = "deposit.swept.success"
    DEPOSIT_SWEPT_FAILED = "deposit.swept.failed"
    WITHDRAW_SUCCESS = "withdraw.success"
    WITHDRAW_FAILED = "withdraw.failed"
    WITHDRAW_CANCELLED = "withdraw.cancelled"
    GATEWAY_DEPOSIT_SUCCESS = "gateway-deposit.success"
    GATEWAY_DEPOSIT_FAILED = "gateway-deposit.failed"
    GATEWAY_DEPOSIT_CANCELLED = "gateway-deposit.cancelled"
    GATEWAY_WITHDRAW_SUCCESS = "gateway-withdraw.success"
    AUTO_SETTLEMENT_SUCCESS = "auto-settlement.success"
    AUTO_SETTLEMENT_FAILED = "auto-settlement.failed"
    AUTO_SETTLEMENT_CANCELLED = "auto-settlement.cancelled"
    SALVAGE_SUCCESS = "salvage.success"
    SALVAGE_FAILED = "salvage.failed"
    SALVAGE_CANCELLED = "salvage.cancelled"


class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    SALVAGE = "SALVAGE"
    AUTO_SETTLEMENT = "AUTO_SETTLEMENT"
    AUTO_FUNDING = "AUTO_FUNDING"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"
    CANCELLED = "CANCELLED"
