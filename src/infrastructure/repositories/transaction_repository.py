from typing import Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from src.infrastructure.repositories.base import Base
from src.models import Transaction
from src.types.common_types import WalletId
from src.types.error import Error, error


class TransactionRepository(Base[Transaction]):
    """
    Concrete implementation of the transaction repository using SQLModel.
    """

    _model = Transaction

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
