from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from src.types.blockrader.base import baseBlockRaderType


class BlockNetwork(baseBlockRaderType):
    blockNetwork_id: str = Field(alias="id")
    createdAt: datetime
    derivationPath: str
    isActive: bool
    isEvmCompatible: bool
    logoUrl: str
    name: str
    slug: str
    symbol: str
    tokenStandard: Optional[str]
    updatedAt: datetime


class AssetInner(baseBlockRaderType):
    address_id: str = Field(alias="id")
    address: str
    blockNetwork: BlockNetwork
    createdAt: datetime
    decimals: int
    isActive: bool
    logoUrl: str
    name: str
    network: str
    standard: Optional[str]
    symbol: str
    updatedAt: datetime


class Asset(baseBlockRaderType):
    asset_id: str = Field(alias="id")
    asset: AssetInner
    createdAt: datetime
    isActive: bool
    updatedAt: datetime


class WalletAnalytics(baseBlockRaderType):
    currentBalance: float
    numberOfAssets: int
    unsweptBalance: float


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


class Meta(baseBlockRaderType):
    currentPage: int
    itemCount: int
    itemsPerPage: int
    totalItems: int
    totalPages: int


class TransactionAsset(baseBlockRaderType):
    transaction_asset_id: str = Field(alias="id")
    address: str
    createdAt: datetime
    decimals: int
    isActive: bool
    logoUrl: str
    name: str
    network: str
    standard: Optional[str]
    symbol: str
    updatedAt: datetime


class TransactionAddress(baseBlockRaderType):
    transaction_address_id: str = Field(alias="id")
    address: str
    configurations: Configurations
    createdAt: datetime
    derivationPath: Optional[str]
    isActive: bool
    metadata: Optional[Any]
    name: Optional[str]
    network: str
    transaction_address_type: str = Field(alias="type")
    updatedAt: datetime


class WalletInfo(baseBlockRaderType):
    wallet_info_id: str = Field(alias="id")


class AMLCheckData(baseBlockRaderType):
    isBlacklisted: bool
