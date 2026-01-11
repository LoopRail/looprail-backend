from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from src.types.blockrader.base import baseBlockRaderType
from src.types.common_types import Address


class BlockchainData(baseBlockRaderType):
    blockchain_id: str = Field(alias="id")
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


class AssetData(baseBlockRaderType):
    asset_id: str = Field(alias="id")
    address: Address
    blockNetwork: BlockchainData | None = None
    createdAt: datetime | None = None
    decimals: int
    isActive: bool
    logoUrl: str
    name: str
    network: str
    standard: Optional[str]
    symbol: str
    updatedAt: datetime | None = None


class Asset(baseBlockRaderType):
    asset_id: str = Field(alias="id")
    asset: AssetData
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
    address: Address
    createdAt: datetime
    decimals: int
    isActive: bool
    logoUrl: str
    name: str
    network: str
    standard: Optional[str]
    symbol: str
    updatedAt: datetime


class AddressData(baseBlockRaderType):
    address_id: str = Field(alias="id")
    address: Address
    configurations: Configurations
    createdAt: datetime
    derivationPath: Optional[str]
    isActive: bool
    metadata: Optional[Any] = (
        None  # Keeping it optional for now, adjust based on context if needed
    )
    name: str  # Made not optional to match webhook_dtos.py
    network: str
    type: str = Field(
        alias="type"
    )  # Renamed from transaction_address_type, made not optional
    updatedAt: datetime


class WalletInfo(baseBlockRaderType):
    wallet_info_id: str = Field(alias="id")


class AMLCheckData(baseBlockRaderType):
    isBlacklisted: bool
