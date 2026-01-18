from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies.auth_deps import get_current_user
from src.api.dependencies.usecases import get_transaction_usecase
from src.dtos.transaction_dtos import TransactionReadList, TransactionResponseBuilder
from src.infrastructure.logger import get_logger
from src.models import User
from src.types.common_types import TransactionId
from src.types.types import TransactionStatus, TransactionType
from src.usecases import TransactionUsecase

logger = get_logger(__name__)


router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: TransactionId,
    current_user: User = Depends(get_current_user),
    transaction_usecase: TransactionUsecase = Depends(get_transaction_usecase),
    include_details: bool = False,
):
    # Get transaction with details eagerly loaded
    transaction, err = await transaction_usecase.get_transaction_by_id(
        transaction_id=transaction_id
    )

    if err:
        logger.error(
            "Error getting transaction with ID %s, Error %s", transaction_id, err
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    if transaction.wallet.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    return TransactionResponseBuilder.from_transaction(
        transaction, include_details=include_details
    )


@router.get("/transactions", response_model=TransactionReadList)
async def list_transactions(
    current_user: User = Depends(get_current_user),
    transaction_usecase: TransactionUsecase = Depends(get_transaction_usecase),
    page: int = 1,
    page_size: int = 20,
    transaction_status: Optional[TransactionStatus] = None,
    transaction_type: Optional[TransactionType] = None,
):
    transactions, total = await transaction_usecase.list_user_transactions(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        transaction_type=transaction_type,
        status=transaction_status,
    )

    return TransactionResponseBuilder.from_transaction_list(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/transactions/wallet/{wallet_id}", response_model=TransactionReadList)
async def list_transactions_by_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    transaction_usecase: TransactionUsecase = Depends(get_transaction_usecase),
    page: int = 1,
    page_size: int = 20,
    transaction_status: Optional[TransactionStatus] = None,
    transaction_type: Optional[TransactionType] = None,
):
    (
        transactions,
        total,
        err,
    ) = await transaction_usecase.list_transactions_by_wallet_id_for_user(
        user_id=current_user.id,
        wallet_id=wallet_id,
        page=page,
        page_size=page_size,
        transaction_type=transaction_type,
        status=transaction_status,
    )

    if err:
        logger.error(
            "Error getting transactions for wallet %s for user %s, Error: %s",
            wallet_id,
            current_user.id,
            err,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transactions",
        )

    return TransactionResponseBuilder.from_transaction_list(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/transactions/asset/{asset_id}", response_model=TransactionReadList)
async def list_transactions_by_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    transaction_usecase: TransactionUsecase = Depends(get_transaction_usecase),
    page: int = 1,
    page_size: int = 20,
    transaction_status: Optional[TransactionStatus] = None,
    transaction_type: Optional[TransactionType] = None,
):
    (
        transactions,
        total,
        err,
    ) = await transaction_usecase.list_transactions_by_asset_id_for_user(
        user_id=current_user.id,
        asset_id=asset_id,
        page=page,
        page_size=page_size,
        transaction_type=transaction_type,
        status=transaction_status,
    )

    if err:
        logger.error(
            "Error getting transactions for asset %s for user %s, Error: %s",
            asset_id,
            current_user.id,
            err,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transactions",
        )

    return TransactionResponseBuilder.from_transaction_list(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
    )
