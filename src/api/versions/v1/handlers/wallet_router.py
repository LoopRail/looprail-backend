from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_current_user, get_user_usecases
from src.dtos import WithdrawalRequest
from src.infrastructure.logger import get_logger
from src.models import User
from src.usecases import WalletManagerUsecase

logger = get_logger(__name__)

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.post("/withdraw", status_code=status.HTTP_200_OK)
async def withdraw(
    req: WithdrawalRequest,
    user: User = Depends(get_current_user),
):
    pass
