from typing import Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from src.infrastructure.repositories.base import Base
from src.models import Transaction
from src.types.common_types import WalletId
from src.types.error import Error, error
from src.types.types import TransactionStatus


class TransactionRepository(Base[Transaction]):
    """
    Concrete implementation of the transaction repository using SQLModel.
    """

    _model = Transaction

    async def get_transactions_by_wallet_id(
        self, *, wallet_id: WalletId, limit: int = 20, offset: int = 0
    ) -> Tuple[list[Transaction], Error]:
        try:
            from sqlalchemy.orm import selectinload
            statement = (
                select(Transaction)
                .options(
                    selectinload(Transaction.bank_transfer),
                    selectinload(Transaction.wallet_transfer),
                    selectinload(Transaction.internal_transfer),
                    selectinload(Transaction.deposit),
                )
                .where(Transaction.wallet_id == wallet_id)
                .where(Transaction.status != TransactionStatus.PENDING)
                .order_by(Transaction.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(statement)
            return result.scalars().all(), None
        except SQLAlchemyError as e:
            return [], error(str(e))
