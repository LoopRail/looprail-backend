from datetime import datetime
from typing import Any, Optional

from src.types import error
from src.types.blockrader.base import (TransactionStatus, TransactionType,
                                       WebhookEventType, baseBlockRaderType)
from src.types.blockrader.dtos import WalletData
from src.types.blockrader.types import (AML, AddressData, AssetData,
                                        BlockchainData)
from src.types.common_types import Address


class WebhookEvent(baseBlockRaderType):
    event: WebhookEventType
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
    status: TransactionStatus
    type: TransactionType
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
    event: WebhookEventType = WebhookEventType.DEPOSIT_SUCCESS
    data: DepositSuccessData


class DepositProcessingData(DepositSuccessData):
    event: WebhookEventType = WebhookEventType.DEPOSIT_PROCESSING
    status: TransactionStatus = TransactionStatus.PROCESSING
    blockNumber: Optional[int] = None
    blockHash: Optional[str] = None
    hash: Optional[str] = None
    confirmations: int = 0
    confirmed: bool = False
    gasPrice: Optional[str] = None
    gasUsed: Optional[str] = None
    gasFee: Optional[str] = None


class WebhookDepositProcessing(WebhookEvent):
    event: WebhookEventType = WebhookEventType.DEPOSIT_PROCESSING
    data: DepositProcessingData


class WithdrawSuccessData(DepositSuccessData):
    event: WebhookEventType = WebhookEventType.WITHDRAW_SUCCESS
    senderAddress: Address
    recipientAddress: Address
    status: TransactionStatus = TransactionStatus.SUCCESS
    type: TransactionType = TransactionType.WITHDRAW


class WebhookWithdrawSuccess(WebhookEvent):
    event: WebhookEventType = WebhookEventType.WITHDRAW_SUCCESS
    data: WithdrawSuccessData


class DepositSweptSuccessData(DepositSuccessData):
    event: WebhookEventType = WebhookEventType.DEPOSIT_SWEPT_SUCCESS
    assetSwept: bool = True
    assetSweptAt: Optional[datetime] = None
    assetSweptGasFee: Optional[str] = None
    assetSweptHash: Optional[str] = None
    assetSweptSenderAddress: Optional[Address] = None
    assetSweptRecipientAddress: Optional[Address] = None
    assetSweptAmount: Optional[str] = None
    reason: Optional[str] = None


class WebhookDepositSweptSuccess(WebhookEvent):
    event: WebhookEventType = WebhookEventType.DEPOSIT_SWEPT_SUCCESS
    data: DepositSweptSuccessData


class DepositFailedData(DepositSuccessData):
    event: WebhookEventType = WebhookEventType.DEPOSIT_FAILED
    status: TransactionStatus = TransactionStatus.FAILED
    amlScreening: AML
    reason: Optional[str] = None


class WebhookDepositFailed(WebhookEvent):
    event: WebhookEventType = WebhookEventType.DEPOSIT_FAILED
    data: DepositFailedData


class WithdrawFailedData(DepositSuccessData):
    event: WebhookEventType = WebhookEventType.WITHDRAW_FAILED
    status: TransactionStatus = TransactionStatus.FAILED
    amlScreening: AML
    reason: Optional[str] = None


class WebhookWithdrawFailed(WebhookEvent):
    event: WebhookEventType = WebhookEventType.WITHDRAW_FAILED
    data: WithdrawFailedData


class DepositSweptFailedData(DepositSweptSuccessData):
    event: WebhookEventType = WebhookEventType.DEPOSIT_SWEPT_FAILED
    assetSwept: bool = False
    reason: Optional[str] = None


class WebhookDepositSweptFailed(WebhookEvent):
    event: WebhookEventType = WebhookEventType.DEPOSIT_SWEPT_FAILED
    data: DepositSweptFailedData


class GatewayDepositSuccessData(DepositSuccessData):
    event: WebhookEventType = WebhookEventType.GATEWAY_DEPOSIT_SUCCESS
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
    event: WebhookEventType = WebhookEventType.GATEWAY_DEPOSIT_SUCCESS
    data: GatewayDepositSuccessData


class GatewayWithdrawSuccessData(DepositSuccessData):
    event: WebhookEventType = WebhookEventType.GATEWAY_WITHDRAW_SUCCESS
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
    event: WebhookEventType = WebhookEventType.GATEWAY_WITHDRAW_SUCCESS
    data: GatewayWithdrawSuccessData


class GenericWebhookEvent(baseBlockRaderType):
    event: WebhookEventType
    data: dict[str, Any]

    def to_specific_event(self) -> Optional[WebhookEvent]:
        WEBHOOK_EVENT_MAP = {
            WebhookEventType.DEPOSIT_SUCCESS: WebhookDepositSuccess,
            WebhookEventType.DEPOSIT_PROCESSING: WebhookDepositProcessing,
            WebhookEventType.WITHDRAW_SUCCESS: WebhookWithdrawSuccess,
            WebhookEventType.DEPOSIT_SWEPT_SUCCESS: WebhookDepositSweptSuccess,
            WebhookEventType.DEPOSIT_FAILED: WebhookDepositFailed,
            WebhookEventType.WITHDRAW_FAILED: WebhookWithdrawFailed,
            WebhookEventType.DEPOSIT_SWEPT_FAILED: WebhookDepositSweptFailed,
            WebhookEventType.GATEWAY_DEPOSIT_SUCCESS: WebhookGatewayDepositSuccess,
            WebhookEventType.GATEWAY_WITHDRAW_SUCCESS: WebhookGatewayWithdrawSuccess,
        }

        event_type = self.event
        if event_type not in WEBHOOK_EVENT_MAP:
            return None

        specific_model = self.WEBHOOK_EVENT_MAP[event_type]
        return specific_model(event=self.event, data=self.data)
