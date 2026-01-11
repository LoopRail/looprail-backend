from fastapi import APIRouter, status

from src.infrastructure.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.post("/withdraw", status_code=status.HTTP_200_OK)
async def withdraw():
    pass
