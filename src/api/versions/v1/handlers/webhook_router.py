from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_asset_repository,
    get_blockrader_webhook_event,
    get_config,
    get_ledger_service,
    get_lock_service,
    get_transaction_repository,
    get_transaction_usecase,
    get_wallet_repository,
)
from src.api.webhooks.registry import get_registry
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import (
    AssetRepository,
    TransactionRepository,
    WalletRepository,
)
from src.infrastructure.services import LedgerService, LockService
from src.types.blockrader import WebhookEvent
from src.usecases.transaction_usecases import TransactionUsecase

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
    asset_repo: AssetRepository = Depends(get_asset_repository),
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    transaction_usecase: TransactionUsecase = Depends(get_transaction_usecase),
    config: Config = Depends(get_config),
    lock_service: LockService = Depends(get_lock_service),
):
    logger.info("Handling BlockRadar webhook event of type: %s", webhook_event.event)
    logger.info("Received BlockRadar webhook event: %s", webhook_event.event)
    registry = get_registry()
    handler = registry.get(webhook_event.event)
    if handler:
        logger.info("Handler found for event %s, processing...", webhook_event.event)
        await handler(
            webhook_event,
            ledger_service=ledger_service,
            wallet_repo=wallet_repo,
            asset_repo=asset_repo,
            transaction_usecase=transaction_usecase,
            lock_service=lock_service,
            config=config,
            transaction_repo=transaction_repo,
        )
        logger.info("Webhook event %s processed successfully.", webhook_event.event)
        return {"message": "Webhook received and processed"}
    logger.warning(
        "No handler found for event: %s. Webhook received but no handler found",
        webhook_event.event,
    )
    return {"message": "Webhook received but no handler found"}
