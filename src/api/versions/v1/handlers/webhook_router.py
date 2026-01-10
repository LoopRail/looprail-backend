from src.usecases.transaction_usecases import TransactionUsecase
from src.api.dependencies.usecases import get_transaction_usecase
from src.api.webhooks import handlers  # noqa: F401
from fastapi import APIRouter, Depends, status, Request
from src.api.dependencies.repositories import get_wallet_repository
from src.api.dependencies.services import get_ledger_service
from src.infrastructure.repositories import WalletRepository
from src.infrastructure.services.ledger import LedgerService
from src.api.dependencies.webhooks import get_blockrader_webhook_event
from src.api.webhooks.registry import get_registry
from src.infrastructure.logger import get_logger
from src.types.blockrader import WebhookEvent

logger = get_logger(__name__)
router = APIRouter(
    prefix="/webhooks",
    tags=["Webhook"],
)


@router.post("/blockrader", status_code=status.HTTP_200_OK)
async def handle_blockrader_webhook(
    webhook_event: WebhookEvent = Depends(get_blockrader_webhook_event),
    ledger_service: LedgerService = Depends(get_ledger_service),
    wallet_repo: WalletRepository = Depends(get_wallet_repository),
    transaction_usecase: TransactionUsecase = Depends(
        get_transaction_usecase
    ),
):
    logger.info("Received BlockRadar webhook event: %s", webhook_event.event)
    registry = get_registry()
    handler = registry.get(webhook_event.event)
    if handler:
        await handler(
            webhook_event,
            ledger_service=ledger_service,
            wallet_repo=wallet_repo,
            transaction_usecase=transaction_usecase,
        )
        return {"message": "Webhook received and processed"}
    logger.warning("No handler found for event: %s", webhook_event.event)
    return {"message": "Webhook received but no handler found"}
