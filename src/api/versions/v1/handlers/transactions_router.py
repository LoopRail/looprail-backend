from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies.usecases import get_transaction_usecase
from src.dtos.transaction_dtos import TransactionRead, TransactionReadList
from src.infrastructure.logger import get_logger
from src.types.common_types import TransactionId
from src.api.dependencies.auth_deps import get_current_user
from src.models import User
from src.usecases import TransactionUsecase

logger = get_logger(__name__)


router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/", response_model=TransactionReadList)
async def get_transactions(
    user: User = Depends(get_current_user),
    usecase: TransactionUsecase = Depends(get_transaction_usecase),
    limit: int = 20,
    offset: int = 0,
):
    transactions, err = await usecase.get_transactions_by_wallet_id(
        wallet_id=user.wallet.id, limit=limit, offset=offset
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err.message)
    return TransactionReadList(transactions=transactions)


@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: TransactionId,
    user: User = Depends(get_current_user),
    usecase: TransactionUsecase = Depends(get_transaction_usecase),
):
    transaction, err = await usecase.get_transaction_by_id(
        transaction_id=transaction_id
    )
    if err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.message)

    if transaction.wallet_id != user.wallet.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this transaction",
        )
    return transaction
