from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


class baseBlockRaderType(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")


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


class baseResponse(baseBlockRaderType):
    message: str
    statusCode: int


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
