from enum import Enum

from pydantic import BaseModel, ConfigDict


class baseBlockRaderType(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, extra="allow", arbitrary_types_allowed=True
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
    SIGNED_SUCCESS = "signed.success"
    SIGNED_FAILED = "signed.failed"
    SIGNED_CANCELLED = "signed.cancelled"
    SWAP_SUCCESS = "swap.success"
    SWAP_FAILED = "swap.failed"
    SWAP_CANCELLED = "swap.cancelled"
    CUSTOM_SMART_CONTRACT_SUCCESS = "custom-smart-contract.success"
    CUSTOM_SMART_CONTRACT_FAILED = "custom-smart-contract.failed"
    CUSTOM_SMART_CONTRACT_CANCELLED = "custom-smart-contract.cancelled"
    STAKING_SUCCESS = "staking.success"
    STAKING_FAILED = "staking.failed"
    STAKING_CANCELLED = "staking.cancelled"
    UNSTAKING_SUCCESS = "unstaking.success"
    UNSTAKING_FAILED = "unstaking.failed"
    UNSTAKING_CANCELLED = "unstaking.cancelled"
    UNSTAKING_WITHDRAW_SUCCESS = "unstaking.withdraw.success"
    UNSTAKING_WITHDRAW_FAILED = "unstaking.withdraw.failed"
    UNSTAKING_WITHDRAW_CANCELLED = "unstaking.withdraw.cancelled"
    RESTAKING_SUCCESS = "restaking.success"
    RESTAKING_FAILED = "restaking.failed"
    RESTAKING_CANCELLED = "restaking.cancelled"
    AUTO_SETTLEMENT_SUCCESS = "auto-settlement.success"
    AUTO_SETTLEMENT_FAILED = "auto-settlement.failed"
    AUTO_SETTLEMENT_CANCELLED = "auto-settlement.cancelled"
    SALVAGE_SUCCESS = "salvage.success"
    SALVAGE_FAILED = "salvage.failed"
    SALVAGE_CANCELLED = "salvage.cancelled"


class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    SIGNED = "SIGNED"
    GATEWAY_DEPOSIT = "GATEWAY_DEPOSIT"
    GATEWAY_WITHDRAW = "GATEWAY_WITHDRAW"
    SALVAGE = "SALVAGE"
    AUTO_SETTLEMENT = "AUTO_SETTLEMENT"
    AUTO_FUNDING = "AUTO_FUNDING"
    STAKING = "STAKING"
    UNSTAKING = "UNSTAKING"
    RESTAKING = "RESTAKING"
    UNSTAKING_WITHDRAW = "UNSTAKING_WITHDRAW"
    CUSTOM_SMART_CONTRACT = "CUSTOM_SMART_CONTRACT"
    SWAP = "SWAP"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"
    CANCELLED = "CANCELLED"
