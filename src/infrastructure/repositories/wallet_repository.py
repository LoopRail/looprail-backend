from typing import Optional, Tuple
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.repositories.base_repository import BaseRepository
from src.models.wallet_model import Wallet, Transaction, WalletRepository
from src.types.error import Error, error


class SQLWalletRepository(WalletRepository, BaseRepository):
    """
    Concrete implementation of the wallet repository using SQLModel.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_wallet(self, *, wallet: Wallet) -> Tuple[Optional[Wallet], Error]:
        return await self._execute_in_transaction(wallet.create, wallet)

    async def get_wallet_by_id(self, *, wallet_id: UUID) -> Tuple[Optional[Wallet], Error]:
        wallet = await Wallet.get(self.session, wallet_id)
        if not wallet:
            return None, error("Wallet not found")
        return wallet, None

    async def get_wallet_by_address(self, *, address: str) -> Tuple[Optional[Wallet], Error]:
        wallet = await Wallet.find_one(self.session, address=address)
        if not wallet:
            return None, error("Wallet not found")
        return wallet, None

    async def get_wallet_by_provider_id(self, *, provider_id: str) -> Tuple[Optional[Wallet], Error]:
        wallet = await Wallet.find_one(self.session, provider_id=provider_id)
        if not wallet:
            return None, error("Wallet not found")
        return wallet, None

    async def get_wallets_by_user_id(self, *, user_id: UUID) -> Tuple[list[Wallet], Error]:
        try:
            wallets = await Wallet.find_all(self.session, user_id=user_id)
            return wallets, None
        except Exception as e:
            return [], error(str(e))

    async def update_wallet(self, *, wallet: Wallet) -> Tuple[Optional[Wallet], Error]:
        return await self._execute_in_transaction(wallet.save, wallet)

    async def create_transaction(
        self, *, transaction: Transaction
    ) -> Tuple[Optional[Transaction], Error]:
        return await self._execute_in_transaction(transaction.create, transaction)

    async def get_transaction_by_id(
        self, *, transaction_id: UUID
    ) -> Tuple[Optional[Transaction], Error]:
        transaction = await Transaction.get(self.session, transaction_id)
        if not transaction:
            return None, error("Transaction not found")
        return transaction, None

    async def get_transactions_by_wallet_id(
        self, *, wallet_id: UUID, limit: int = 20, offset: int = 0
    ) -> Tuple[list[Transaction], Error]:
        try:
            statement = (
                select(Transaction)
                .where(Transaction.wallet_id == wallet_id)
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.exec(statement)
            return result.all(), None
        except Exception as e:
            return [], error(str(e))

    async def get_transaction_by_hash(
        self, *, transaction_hash: str
    ) -> Tuple[Optional[Transaction], Error]:
        transaction = await Transaction.find_one(
            self.session, transaction_hash=transaction_hash
        )
        if not transaction:
            return None, error("Transaction not found")
        return transaction, None