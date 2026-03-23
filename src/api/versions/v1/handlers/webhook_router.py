from fastapi import APIRouter, Depends, status, Request, HTTPException
import hmac
import hashlib

from src.api.dependencies import (
    get_asset_repository,
    get_blockrader_webhook_event,
    get_config,
    get_ledger_service,
    get_lock_service,
    get_notification_usecase,
    get_resend_service,
    get_rq_manager,
    get_session_repository,
    get_transaction_repository,
    get_transaction_usecase,
    get_user_repository,
    get_verify_webhook_request,
    get_wallet_repository,
)
from src.api.webhooks.registry import get_registry
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.redis import RQManager
from src.infrastructure.repositories import (
    AssetRepository,
    SessionRepository,
    TransactionRepository,
    UserRepository,
    WalletRepository,
)
from src.models import Transaction, BankTransferDetail
from src.types.types import TransactionStatus
from src.utils.notification_helpers import enqueue_notifications_for_user
from src.types.notification_types import NotificationAction
from src.infrastructure.services import LedgerService, LockService
from src.infrastructure.services.resend_service import ResendService
from src.infrastructure.settings import ENVIRONMENT
from src.types.blockrader import WebhookEvent
from src.types.common_types import Network
from src.usecases.notification_usecases import NotificationUseCase
from src.usecases.transaction_usecases import TransactionUsecase

logger = get_logger(__name__)
router = APIRouter(
    prefix="/webhooks",
    tags=["Webhook"],
    dependencies=[Depends(get_verify_webhook_request)],
)


@router.post("/paycrest", status_code=status.HTTP_200_OK)
async def handle_paycrest_webhook(
    request: Request,
    config: Config = Depends(get_config),
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    transaction_usecase: TransactionUsecase = Depends(get_transaction_usecase),
    notification_usecase: NotificationUseCase = Depends(get_notification_usecase),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    signature = request.headers.get("X-Paycrest-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="No signature")

    body = await request.body()
    secret = config.paycrest.paycrest_api_secret.encode('utf-8')
    calculated_signature = hmac.new(secret, body, hashlib.sha256).hexdigest()

    if signature != calculated_signature:
        logger.warning("Invalid Paycrest signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    logger.info("Received Paycrest webhook: %s", payload)

    event = payload.get("event")
    data = payload.get("data", {})
    paycrest_txn_id = data.get("id")

    if not paycrest_txn_id or not event:
        return {"message": "Ignored missing TX ID or event"}

    from sqlmodel import select
    statement = (
        select(Transaction)
        .join(BankTransferDetail)
        .where(BankTransferDetail.paycrest_txn_id == paycrest_txn_id)
    )
    result = await transaction_repo.session.execute(statement)
    transaction = result.scalar_one_or_none()

    if not transaction:
        logger.warning("No transaction found for Paycrest ID: %s", paycrest_txn_id)
        return {"message": "Transaction not found"}

    # Reload transaction with relationships
    transaction, err = await transaction_repo.find_one(
        id=transaction.id, load=["bank_transfer", "wallet"]
    )

    if transaction.bank_transfer:
        transaction.bank_transfer.paycrest_status = event
        await transaction_repo.update(transaction.bank_transfer)

    if event == "validated":
        if transaction.bank_transfer and transaction.wallet:
            rcpt_name = transaction.bank_transfer.account_name or "the recipient"
            await enqueue_notifications_for_user(
                user_id=str(transaction.wallet.user_id),
                session_repo=session_repo,
                notification_usecase=notification_usecase,
                title="Funds Delivered",
                body=f"Your transfer to {rcpt_name} has been received successfully.",
                action=NotificationAction.WITHDRAWAL_CONFIRMED,
                data={"transaction_id": str(transaction.id)},
            )
    elif event == "settled":
        await transaction_usecase.update_transaction_status(
            transaction_id=transaction.id,
            new_status=TransactionStatus.COMPLETED
        )
    elif event in ["refunded", "expired"]:
        await transaction_usecase.update_transaction_status(
            transaction_id=transaction.id,
            new_status=TransactionStatus.FAILED,
            error_message=f"Paycrest order {event}"
        )

    return {"message": "Webhook processed successfully"}


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
    session_repo: SessionRepository = Depends(get_session_repository),
    notification_usecase: NotificationUseCase = Depends(get_notification_usecase),
    user_repo: UserRepository = Depends(get_user_repository),
    resend_service: ResendService = Depends(get_resend_service),
    rq_manager: RQManager = Depends(get_rq_manager),
):
    logger.info("Handling BlockRadar webhook event of type: %s", webhook_event.event)
    logger.info("Received BlockRadar webhook event: %s", webhook_event.event)
    if (
        config.app.environment == ENVIRONMENT.PRODUCTION
        and webhook_event.data.network == Network.TESTNET
    ):
        logger.warning(
            "Ignoring testnet webhook event of type %s in production: %s",
            webhook_event.event,
            webhook_event.data.id,
        )
        return {"message": "Webhook ignored in production environment"}

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
            session_repo=session_repo,
            notification_usecase=notification_usecase,
            user_repo=user_repo,
            resend_service=resend_service,
            rq_manager=rq_manager,
        )
        logger.info("Webhook event %s processed successfully.", webhook_event.event)
        return {"message": "Webhook received and processed"}
    logger.warning(
        "No handler found for event: %s. Webhook received but no handler found",
        webhook_event.event,
    )
    return {"message": "Webhook received but no handler found"}
