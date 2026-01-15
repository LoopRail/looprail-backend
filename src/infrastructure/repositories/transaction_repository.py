from typing import Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models import Transaction
from src.types.common_types import TransactionId, WalletId
from src.types.error import Error, error


class TransactionRepository:
    """
    Concrete implementation of the transaction repository using SQLModel.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_transaction(
        self, *, transaction: Transaction
    ) -> Tuple[Optional[Transaction], Error]:
        return await transaction.create(self.session)

    async def get_transaction_by_id(
        self, *, transaction_id: TransactionId
    ) -> Tuple[Optional[Transaction], Error]:
        transaction = await Transaction.get(self.session, transaction_id)
        if not transaction:
            return None, error("Transaction not found")
        return transaction, None

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
        transaction = await Transaction.find_one(
            self.session, transaction_hash=transaction_hash
        )
        if not transaction:
            return None, error("Transaction not found")
        return transaction, None

    async def get_transaction_by_provider_id(
        self, *, provider_id: str
    ) -> Tuple[Optional[Transaction], Error]:
        transaction = await Transaction.find_one(self.session, provider_id=provider_id)
        if not transaction:
            return None, error("Transaction not found")
        return transaction, None

    async def update_transaction(
        self, *, transaction: Transaction
    ) -> Tuple[Optional[Transaction], Error]:
        err = await transaction.save(self.session)
        if err:
            return None, err
        return transaction, None
