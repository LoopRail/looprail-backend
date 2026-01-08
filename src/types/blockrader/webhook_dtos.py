from datetime import datetime
from typing import Any, Optional

from src.types.blockrader.base import baseBlockRaderType
from src.types.blockrader.dtos import WalletData
from src.types.blockrader.types import (AML, AddressData, AssetData,
                                        BlockchainData)
from src.types.common_types import Address


class WebhookEvent(baseBlockRaderType):
    event: str
    data: Any


class DepositSuccessData(baseBlockRaderType):
    id: str
    reference: str
    senderAddress: Address
    recipientAddress: Address
    amount: str
    amountPaid: str
    fee: Optional[str] = None
    currency: str
    blockNumber: Optional[int] = None
    blockHash: Optional[str] = None
    hash: Optional[str] = None
    confirmations: int
    confirmed: bool
    gasPrice: Optional[str] = None
    gasUsed: Optional[str] = None
    gasFee: Optional[str] = None
    status: str
    type: str
    note: Optional[str] = None
    amlScreening: AML
    assetSwept: Optional[bool] = None
    assetSweptAt: Optional[datetime] = None
    assetSweptGasFee: Optional[str] = None
    assetSweptHash: Optional[str] = None
    assetSweptSenderAddress: Optional[Address] = None
    assetSweptRecipientAddress: Optional[Address] = None
    assetSweptAmount: Optional[str] = None
    reason: Optional[str] = None
    network: str
    chainId: Optional[int] = None
    metadata: Optional[Any] = None  # Can be a dict
    createdAt: datetime
    updatedAt: datetime
    asset: AssetData
    address: AddressData
    blockchain: BlockchainData
    wallet: WalletData
    beneficiary: Optional[Any] = None


class WebhookDepositSuccess(WebhookEvent):
    event: str = "deposit.success"
    data: DepositSuccessData


class DepositProcessingData(DepositSuccessData):
    event: str = "deposit.processing"
    status: str = "PROCESSING"
    blockNumber: Optional[int] = None
    blockHash: Optional[str] = None
    hash: Optional[str] = None
    confirmations: int = 0
    confirmed: bool = False
    gasPrice: Optional[str] = None
    gasUsed: Optional[str] = None
    gasFee: Optional[str] = None


class WebhookDepositProcessing(WebhookEvent):
    event: str = "deposit.processing"
    data: DepositProcessingData


class WithdrawSuccessData(DepositSuccessData):
    event: str = "withdraw.success"
    senderAddress: Address
    recipientAddress: Address
    status: str = "SUCCESS"
    type: str = "WITHDRAW"


class WebhookWithdrawSuccess(WebhookEvent):
    event: str = "withdraw.success"
    data: WithdrawSuccessData


class SignedSuccessData(DepositSuccessData):
    event: str = "signed.success"
    tokenAddress: Optional[Address] = None
    amountUSD: Optional[str] = None
    rateUSD: Optional[str] = None
    feeHash: Optional[str] = None
    currency: str
    toCurrency: Optional[str] = None
    signedTransaction: Optional[str] = None
    rate: Optional[str] = None


class WebhookSignedSuccess(WebhookEvent):
    event: str = "signed.success"
    data: SignedSuccessData


class DepositSweptSuccessData(DepositSuccessData):
    event: str = "deposit.swept.success"
    assetSwept: bool = True
    assetSweptAt: Optional[datetime] = None
    assetSweptGasFee: Optional[str] = None
    assetSweptHash: Optional[str] = None
    assetSweptSenderAddress: Optional[Address] = None
    assetSweptRecipientAddress: Optional[Address] = None
    assetSweptAmount: Optional[str] = None
    reason: Optional[str] = None


class WebhookDepositSweptSuccess(WebhookEvent):
    event: str = "deposit.swept.success"
    data: DepositSweptSuccessData


class DepositFailedData(DepositSuccessData):
    event: str = "deposit.failed"
    status: str = "FAILED"
    amlScreening: AML
    reason: Optional[str] = None


class WebhookDepositFailed(WebhookEvent):
    event: str = "deposit.failed"
    data: DepositFailedData


class WithdrawFailedData(DepositSuccessData):
    event: str = "withdraw.failed"
    status: str = "FAILED"
    amlScreening: AML
    reason: Optional[str] = None


class WebhookWithdrawFailed(WebhookEvent):
    event: str = "withdraw.failed"
    data: WithdrawFailedData


class DepositSweptFailedData(DepositSweptSuccessData):
    event: str = "deposit.swept.failed"
    assetSwept: bool = False
    reason: Optional[str] = None


class WebhookDepositSweptFailed(WebhookEvent):
    event: str = "deposit.swept.failed"
    data: DepositSweptFailedData


class GatewayDepositSuccessData(DepositSuccessData):
    event: str = "gateway-deposit.success"
    tokenAddress: Address
    amountUSD: Optional[str] = None
    rateUSD: Optional[str] = None
    currency: str
    amlScreening: AML
    metadata: Optional[Any] = None
    toCurrency: Optional[str] = None
    signedTransaction: Optional[str] = None
    rate: Optional[str] = None


class WebhookGatewayDepositSuccess(WebhookEvent):
    event: str = "gateway-deposit.success"
    data: GatewayDepositSuccessData


class GatewayWithdrawSuccessData(DepositSuccessData):
    event: str = "gateway-withdraw.success"
    tokenAddress: Address
    amountUSD: Optional[str] = None
    rateUSD: Optional[str] = None
    currency: str
    amlScreening: AML
    metadata: Optional[Any] = None
    toCurrency: Optional[str] = None
    signedTransaction: Optional[str] = None
    rate: Optional[str] = None


class WebhookGatewayWithdrawSuccess(WebhookEvent):
    event: str = "gateway-withdraw.success"
    data: GatewayWithdrawSuccessData


# Generic Webhook model for parsing the event type
class GenericWebhookEvent(baseBlockRaderType):
    event: str
    data: dict[str, Any]  # Use dict to allow dynamic parsing

    WEBHOOK_EVENT_MAP = {
        "deposit.success": WebhookDepositSuccess,
        "deposit.processing": WebhookDepositProcessing,
        "withdraw.success": WebhookWithdrawSuccess,
        "signed.success": WebhookSignedSuccess,
        "deposit.swept.success": WebhookDepositSweptSuccess,
        "deposit.failed": WebhookDepositFailed,
        "withdraw.failed": WebhookWithdrawFailed,
        "deposit.swept.failed": WebhookDepositSweptFailed,
        "gateway-deposit.success": WebhookGatewayDepositSuccess,
        "gateway-withdraw.success": WebhookGatewayWithdrawSuccess,
    }

    def to_specific_event(self) -> WebhookEvent:
        event_type = self.event
        if event_type not in self.WEBHOOK_EVENT_MAP:
            raise ValueError(f"Unknown webhook event type: {event_type}")

        specific_model = self.WEBHOOK_EVENT_MAP[event_type]
        return specific_model(event=self.event, data=self.data)
