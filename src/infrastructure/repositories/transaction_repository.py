from typing import Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from src.infrastructure.repositories.base import Base
from src.models import Transaction
from src.types.common_types import TransactionId, WalletId
from src.types.error import Error, error


class TransactionRepository(Base):
    """
    Concrete implementation of the transaction repository using SQLModel.
    """

    _model = Transaction

    async def create_transaction(
        self, *, transaction: Transaction
    ) -> Tuple[Optional[Transaction], Error]:
        return await self.create(transaction)

    async def get_transaction_by_id(
        self, *, transaction_id: TransactionId
    ) -> Tuple[Optional[Transaction], Error]:
        return await self.get(transaction_id)

    async def get_transactions_by_wallet_id(
        self, *, wallet_id: WalletId, limit: int = 20, offset: int = 0
    ) -> Tuple[list[Transaction], Error]:
        try:
            statement = (
                select(Transaction)
                .where(Transaction.wallet_id == wallet_id)
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(statement)
            return result.scalars().all(), None
        except SQLAlchemyError as e:
            return [], error(str(e))

    async def get_transaction_by_hash(
        self, *, transaction_hash: str
    ) -> Tuple[Optional[Transaction], Error]:
        return await self.find_one(transaction_hash=transaction_hash)

    async def get_transaction_by_provider_id(
        self, *, provider_id: str
    ) -> Tuple[Optional[Transaction], Error]:
        return await self.find_one(provider_id=provider_id)

    async def update_transaction(
        self, *, transaction: Transaction
    ) -> Tuple[Optional[Transaction], Error]:
        return await self.update(transaction)
