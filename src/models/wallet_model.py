from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from src.models.base import Base
from src.models.user_model import User
from src.types.common_types import Address, Chain
from src.types.types import AssetType, TokenStandard

if TYPE_CHECKING:
    from src.models.tranaction_model import Transaction


class Wallet(Base, table=True):
    __tablename__ = "wallets"
    __id_prefix__ = "wlt_"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    address: Address = Field(unique=True, index=True, nullable=False)
    chain: Chain = Field(nullable=False)
    provider: str = Field(index=True, nullable=False)
    ledger_id: str = Field(index=True, nullable=False)
    is_active: bool = Field(default=True, nullable=False)

    name: Optional[str] = Field(default=None)
    derivation_path: Optional[str] = Field(default=None)
    user: User = Relationship(back_populates="wallet")

    transactions: List["Transaction"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    assets: List["Asset"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"passive_deletes": True},
    )


class Asset(Base, table=True):
    __tablename__ = "assets"
    __id_prefix__ = "ast_"

    wallet_id: UUID = Field(
        foreign_key="wallets.id",
        index=True,
    )
    ledger_balance_id: str = Field(default=None, nullable=False, unique=True)
    name: str = Field(nullable=False)
    blockrader_asset_id: UUID = Field(index=True, nullable=False)
    asset_type: AssetType = Field(nullable=False)
    address: Address = Field(nullable=False)
    symbol: str = Field(nullable=False)
    decimals: int = Field(nullable=False)
    address: Address = Field(nullable=False)
    network: str = Field(nullable=False)
    standard: Optional[TokenStandard] = Field(default=None)
    is_active: bool = Field(default=True, nullable=False)

    wallet: Wallet = Relationship(
        back_populates="assets",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    transactions: List["Transaction"] = Relationship(
        back_populates="asset",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    def get_id_prefix(self) -> str:
        return f"{self.__id_prefix__}{self.asset_type.value}_"
