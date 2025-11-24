from fastapi import APIRouter

from src.infrastructure.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/blockrader", tags=["Webhook", "blockrader"])
