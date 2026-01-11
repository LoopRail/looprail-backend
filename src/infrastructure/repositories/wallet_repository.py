from typing import Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models.wallet_model import Wallet
from src.types.common_types import UserId, WalletId
from src.types.error import Error, error


class WalletRepository:
    """
    Concrete implementation of the wallet repository using SQLModel.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_wallet(self, *, wallet: Wallet) -> Tuple[Optional[Wallet], Error]:
        return await wallet.create(self.session)

    async def get_wallet_by_id(
        self, *, wallet_id: WalletId
    ) -> Tuple[Optional[Wallet], Error]:
        wallet = await Wallet.get(self.session, wallet_id)
        if not wallet:
            return None, error("Wallet not found")
        return wallet, None

    async def get_wallet_by_address(
        self, *, address: str
    ) -> Tuple[Optional[Wallet], Error]:
        wallet = await Wallet.find_one(self.session, address=address)
        if not wallet:
            return None, error("Wallet not found")
        return wallet, None

    async def get_wallet_by_provider_id(
        self, *, provider_id: str
    ) -> Tuple[Optional[Wallet], Error]:
        wallet = await Wallet.find_one(self.session, provider_id=provider_id)
        if not wallet:
            return None, error("Wallet not found")
        return wallet, None

    async def get_wallets_by_user_id(
        self, *, user_id: UserId
    ) -> Tuple[list[Wallet], Error]:
        try:
            wallets = await Wallet.find_all(self.session, user_id=user_id)
            return wallets, None
        except SQLAlchemyError as e:
            return [], error(str(e))

    async def update_wallet(self, *, wallet: Wallet) -> Tuple[Optional[Wallet], Error]:
        err = await wallet.save(self.session)
        if err:
            return None, err
        return wallet, None


