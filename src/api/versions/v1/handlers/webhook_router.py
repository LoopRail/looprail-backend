from src.usecases.transaction_usecases import TransactionUsecase
from src.api.dependencies.usecases import get_transaction_usecase
from src.api.webhooks import handlers  # noqa: F401
from fastapi import APIRouter, Depends, status
from src.api.dependencies.repositories import (
    get_wallet_repository,
    get_asset_repository,
)
from src.api.dependencies.services import get_ledger_service
from src.api.dependencies import get_config
from src.infrastructure.config_settings import Config
from src.infrastructure.repositories import WalletRepository, AssetRepository
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
    asset_repo: AssetRepository = Depends(get_asset_repository),
    transaction_usecase: TransactionUsecase = Depends(get_transaction_usecase),
    config: Config = Depends(get_config),
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
            config=config,
        )
        logger.info("Webhook event %s processed successfully.", webhook_event.event)
        return {"message": "Webhook received and processed"}
    logger.warning(
        "No handler found for event: %s. Webhook received but no handler found",
        webhook_event.event,
    )
    return {"message": "Webhook received but no handler found"}
