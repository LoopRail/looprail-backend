from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.types.chain_types import Chain


class baseBlockRaderType(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")


class baseResponse(baseBlockRaderType):
    message: str
    statusCode: int


# Common Models
class Blockchain(baseBlockRaderType):
    createdAt: datetime
    derivationPath: str
    id: str
    isActive: bool
    isEvmCompatible: bool
    logoUrl: str
    name: str
    slug: str
    symbol: str
    tokenStandard: Optional[str]
    updatedAt: datetime


class AssetInner(baseBlockRaderType):
    address: str
    blockchain: Blockchain
    createdAt: datetime
    decimals: int
    id: str
    isActive: bool
    logoUrl: str
    name: str
    network: str
    standard: Optional[str]
    symbol: str
    updatedAt: datetime


class Asset(baseBlockRaderType):
    asset: AssetInner
    createdAt: datetime
    id: str
    isActive: bool
    updatedAt: datetime


# Models for Get Wallet Details
class WalletAnalytics(baseBlockRaderType):
    currentBalance: float
    numberOfAssets: int
    unsweptBalance: float


class WalletDetailsData(baseBlockRaderType):
    address: str
    analytics: WalletAnalytics
    assets: List[Asset]
    blockchain: Blockchain
    createdAt: datetime
    derivationPath: str
    description: str
    id: str
    isActive: bool
    name: str
    network: str
    status: str
    updatedAt: datetime


class WalletBalanceData(baseBlockRaderType):
    asset: Asset
    balance: str
    convertedBalance: str


class Analytics(baseBlockRaderType):
    activeAddressesCount: int | None = None
    addressLimit: int | None = None
    addressesCount: int | None = None
    externalAddressesCount: int | None = None
    inactiveAddressesCount: int | None = None
    internalAddressesCount: int | None = None


class AML(baseBlockRaderType):
    message: str
    provider: str
    status: str


class Configurations(baseBlockRaderType):
    aml: AML
    disableAutoSweep: bool
    enableGaslessWithdraw: bool
    showPrivateKey: bool


class Data(baseBlockRaderType):
    address: str
    blockchain: Blockchain
    configurations: Configurations
    createdAt: datetime
    derivationPath: Optional[str]
    id: str
    isActive: bool
    metadata: Optional[Any]
    name: Optional[str]
    network: str
    type: str
    updatedAt: datetime


class Meta(baseBlockRaderType):
    currentPage: int
    itemCount: int
    itemsPerPage: int
    totalItems: int
    totalPages: int


class TransactionAsset(baseBlockRaderType):
    address: str
    createdAt: datetime
    decimals: int
    id: str
    isActive: bool
    logoUrl: str
    name: str
    network: str
    standard: Optional[str]
    symbol: str
    updatedAt: datetime


class TransactionAddress(baseBlockRaderType):
    address: str
    configurations: Configurations
    createdAt: datetime
    derivationPath: Optional[str]
    id: str
    isActive: bool
    metadata: Optional[Any]
    name: Optional[str]
    network: str
    type: str
    updatedAt: datetime


class TransactionData(baseBlockRaderType):
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
    assetSweptRecipientAddress: Optional[str] = None
    assetSweptSenderAddress: Optional[str] = None
    blockHash: Optional[str] = None
    blockNumber: Optional[int] = None
    blockchain: Blockchain
    chainId: int
    confirmations: int
    confirmed: bool
    createdAt: datetime
    currency: str
    fee: Optional[str] = None
    gasFee: str
    gasPrice: str
    gasUsed: str
    hash: str
    id: str
    metadata: Optional[Any] = None
    network: str
    note: Optional[Any] = None
    reason: Optional[str] = None
    recipientAddress: str
    reference: str
    senderAddress: str
    status: str
    type: str
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


class WalletInfo(baseBlockRaderType):
    id: str


class WithdrawalData(baseBlockRaderType):
    amlScreening: Optional[AML] = None
    amount: str
    amountPaid: str
    asset: AssetInner
    assetSwept: Optional[bool] = None
    assetSweptAmount: Optional[str] = None
    assetSweptAt: Optional[datetime] = None
    assetSweptGasFee: Optional[str] = None
    assetSweptHash: Optional[str] = None
    assetSweptRecipientAddress: Optional[str] = None
    assetSweptResponse: Optional[Any] = None
    assetSweptSenderAddress: Optional[str] = None
    blockHash: Optional[str] = None
    blockNumber: Optional[int] = None
    blockchain: Blockchain
    chainId: Optional[int] = None
    confirmations: Optional[int] = None
    confirmed: bool
    createdAt: datetime
    currency: str
    fee: Optional[str] = None
    feeMetadata: Optional[Any] = None
    gasFee: Optional[str] = None
    gasPrice: Optional[str] = None
    gasUsed: Optional[str] = None
    hash: str
    id: str
    metadata: Optional[Any] = None
    network: str
    note: Optional[Any] = None
    reason: Optional[str] = None
    recipientAddress: str
    senderAddress: str
    status: str
    tokenAddress: Optional[str] = None
    type: str
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
    address: str
    amount: str
    assetId: str


class WithdrawalRequest(baseBlockRaderType):
    assetId: str
    address: str
    amount: str
    reference: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class AMLCheckData(baseBlockRaderType):
    isBlacklisted: bool


class AMLCheckResponse(baseResponse):
    data: AMLCheckData | None = None


class AMLCheckRequest(baseBlockRaderType):
    address: str
    blockchain: Chain
