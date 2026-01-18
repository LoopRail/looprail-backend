from decimal import Decimal
from typing import List, Optional

from pydantic import Field, field_validator
import pydantic

from src.dtos.base import Base
from src.dtos.user_dtos import UserPublic
from src.types.common_types import AssetId, WalletId
from src.types.types import AssetType, InstitutionCountry, TokenStandard


class VerifyAccountRequest(Base):
    # institution: str
    account_identifier: str
    institution_code: str | None = Field(
        default=None,
    )
    institution_country: InstitutionCountry


class VerifyAccountResponse(Base):
    status: str | bool
    message: str
    data: str

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, value: str):
        if not isinstance(value, str):
            return value["account_name"]
        return value


class AssetBalance(Base):
    asset_id: AssetId = Field(alias="asset-id")
    name: str
    symbol: str
    decimals: int
    asset_type: AssetType = Field(alias="asset-type")

    # Balance info
    balance: Decimal = Field(default=Decimal("0"))

    # Metadata
    network: str
    address: str
    standard: Optional[TokenStandard] = None
    is_active: bool = Field(alias="is-active")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class WalletWithAssets(Base):
    id: WalletId
    address: str
    chain: str
    provider: str
    is_active: bool = Field(alias="is-active")
    assets: List[AssetBalance]

    model_config = pydantic.ConfigDict(populate_by_name=True)


class UserAccountResponse(Base):
    user: UserPublic
    wallet: Optional[WalletWithAssets] = None
