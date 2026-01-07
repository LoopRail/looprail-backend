from datetime import datetime
from typing import Any, List, Optional

from pydantic import Field

from src.types.blockrader.base import baseBlockRaderType, baseResponse
from src.types.blockrader.types import (AML, AMLCheckData, Analytics, Asset,
                                        AssetInner, BlockNetwork, Configurations,
                                        Meta, TransactionAddress,
                                        TransactionAsset, WalletInfo)
from src.types.common_types import Address
from src.types.types import Chain


class WalletDetailsData(baseBlockRaderType):
    wallet_id: str = Field(alias="id")
    address: Address
    analytics: Analytics
    assets: List[Asset]
    blockNetwork: BlockNetwork
    createdAt: datetime
    derivationPath: str
    description: str
    isActive: bool
    name: str
    network: str
    status: str
    updatedAt: datetime


class WalletBalanceData(baseBlockRaderType):
    asset: Asset
    balance: str
    convertedBalance: str


class Data(baseBlockRaderType):
    data_id: str = Field(alias="id")
    data_type: str = Field(alias="type")
    address: Address
    blockNetwork: BlockNetwork
    configurations: Configurations
    createdAt: datetime
    derivationPath: Optional[str]
    isActive: bool
    metadata: Optional[Any]
    name: Optional[str]
    network: str
    updatedAt: datetime


class TransactionData(baseBlockRaderType):
    transaction_hash: str = Field(alias="hash")
    transaction_id: str = Field(alias="id")
    transaction_type: str = Field(alias="type")

    address: TransactionAddress
    amlScreening: AML
    amount: str
    amountPaid: str
    asset: TransactionAsset
    assetSwept: bool
    assetSweptAmount: Optional[str] = None
    assetSweptAt: Optional[datetime] = None
    assetSweptGasFee: Optional[str] = None
    assetSweptHash: Optional[str] = None
    assetSweptRecipientAddress: Optional[Address] = None
    assetSweptSenderAddress: Optional[Address] = None
    blockHash: Optional[str] = None
    blockNumber: Optional[int] = None
    blockNetwork: BlockNetwork
    NetworkId: int
    confirmations: int
    confirmed: bool
    createdAt: datetime
    currency: str
    fee: Optional[str] = None
    gasFee: str
    gasPrice: str
    gasUsed: str
    metadata: Optional[Any] = None
    network: str
    note: Optional[Any] = None
    reason: Optional[str] = None
    recipientAddress: Address
    reference: str
    senderAddress: Address
    status: str
    updatedAt: datetime


class WalletAddressResponse(baseResponse):
    analytics: Analytics | None = None
    data: List[Data] | None = None
    meta: Meta | None = None


class WalletDetailsResponse(baseResponse):
    data: WalletDetailsData | None = None


class WalletBalanceResponse(baseResponse):
    data: WalletBalanceData | List[WalletBalanceData] | None = None


class WalletAddressDetailResponse(baseResponse):
    data: Data | None = None


class TransactionResponse(baseResponse):
    data: List[TransactionData] | TransactionData | None = None
    meta: Meta | None = None


class NetworkFeeData(baseBlockRaderType):
    nativeBalance: str
    networkFee: str


class NetworkFeeResponse(baseResponse):
    data: NetworkFeeData | None = None


class WithdrawalData(baseBlockRaderType):
    transaction_hash: str = Field(alias="hash")
    transaction_id: str = Field(alias="id")
    transaction_type: str = Field(alias="type")
    amlScreening: Optional[AML] = None
    amount: str
    amountPaid: str
    asset: AssetInner
    assetSwept: Optional[bool] = None
    assetSweptAmount: Optional[str] = None
    assetSweptAt: Optional[datetime] = None
    assetSweptGasFee: Optional[str] = None
    assetSweptHash: Optional[str] = None
    assetSweptRecipientAddress: Optional[Address] = None
    assetSweptResponse: Optional[Any] = None
    assetSweptSenderAddress: Optional[Address] = None
    blockHash: Optional[str] = None
    blockNumber: Optional[int] = None
    blockNetwork: BlockNetwork
    NetworkId: Optional[int] = None
    confirmations: Optional[int] = None
    confirmed: bool
    createdAt: datetime
    currency: str
    fee: Optional[str] = None
    feeMetadata: Optional[Any] = None
    gasFee: Optional[str] = None
    gasPrice: Optional[str] = None
    gasUsed: Optional[str] = None
    metadata: Optional[Any] = None
    network: str
    note: Optional[Any] = None
    reason: Optional[str] = None
    recipientAddress: Address
    senderAddress: Address
    status: str
    tokenAddress: Optional[str] = None
    updatedAt: datetime
    wallet: WalletInfo


class WithdrawalResponse(baseResponse):
    data: WithdrawalData | None = None


class CreateAddressRequest(baseBlockRaderType):
    metadata: dict[str, any]
    name: str
    disableAutoSweep: bool = Field(default=False)
    enableGaslessWithdraw: bool = Field(default=True)
    showPrivateKey: bool = Field(default=False)


class NetworkFeeRequest(baseBlockRaderType):
    address: Address
    amount: str
    assetId: str


class WithdrawalRequest(baseBlockRaderType):
    assetId: str
    address: Address
    amount: str
    reference: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class AMLCheckResponse(baseResponse):
    data: AMLCheckData | None = None


class AMLCheckRequest(baseBlockRaderType):
    address: Address
    blockNetwork: Chain
