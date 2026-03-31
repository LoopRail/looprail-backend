from typing import Tuple, Optional

from sqlalchemy import func
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
    ) -> Tuple[list[Transaction], int, Error]:
        try:
            from sqlalchemy.orm import selectinload

            base_filter = (
                Transaction.wallet_id == wallet_id,
                Transaction.status != TransactionStatus.PENDING,
            )

            count_result = await self.session.execute(
                select(func.count()).select_from(Transaction).where(*base_filter)
            )
            total = count_result.scalar_one()

            statement = (
                select(Transaction)
                .options(
                    selectinload(Transaction.bank_transfer),
                    selectinload(Transaction.wallet_transfer),
                    selectinload(Transaction.internal_transfer),
                    selectinload(Transaction.deposit),
                )
                .where(*base_filter)
                .order_by(Transaction.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(statement)
            return result.scalars().all(), total, None
        except SQLAlchemyError as e:
            return [], 0, error(str(e))

    async def get_by_paycrest_txn_id(
        self, paycrest_txn_id: str
    ) -> Tuple[Optional[Transaction], Optional[Error]]:
        try:
            from src.models import BankTransferDetail
            statement = (
                select(Transaction)
                .join(BankTransferDetail)
                .where(BankTransferDetail.paycrest_txn_id == paycrest_txn_id)
            )
            result = await self.session.execute(statement)
            return result.scalars().first(), None
        except SQLAlchemyError as e:
            return None, error(str(e))
