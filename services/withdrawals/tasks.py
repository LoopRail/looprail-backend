import asyncio
import logging
from typing import Any, Dict

from rq import Queue
from sqlalchemy.ext.asyncio import AsyncSession

from services.withdrawals.dependencies import TaskDependenciesFactory
from src.infrastructure.config_settings import load_config
from src.infrastructure.db import get_session
from src.infrastructure.redis import RQManager
from src.infrastructure.repositories import SessionRepository, UserRepository
from src.infrastructure.services.resend_service import ResendService
from src.infrastructure.settings import AppSettings, RedisConfig, ResendConfig
from src.types.common_types import UserId
from src.types.notification_types import NotificationAction, NotificationMessages
from src.utils.email_helpers import send_transactional_email

logger = logging.getLogger(__name__)


async def _send_withdrawal_processed_notification(
    user_id: str, transaction_id: str, session: AsyncSession
):
    """
    Enqueue a WITHDRAWAL_PROCESSED push notification for the user.
    Uses the provided session to avoid redundant session creation.
    """
    redis_config = RedisConfig()  # TODO: we should not be creating a new object here
    rq_manager = RQManager(redis_config)

    notif_queue = Queue("notifications", connection=rq_manager.get_connection())

    session_repo = SessionRepository(session)
    sessions = await session_repo.get_user_sessions(user_id)
    for s in sessions:
        if not s.allow_notifications or not s.fcm_token:
            continue
        notif_queue.enqueue(
            "services.notifications.tasks.send_push_notification_task",
            {
                "user_id": str(user_id),
                "token": s.fcm_token,
                "title": "Withdrawal Processed ✅",
                "body": "Your withdrawal has been successfully processed.",
                "action": NotificationAction.WITHDRAWAL_PROCESSED.value,
                "data": {"transaction_id": transaction_id or ""},
                "type": "push",
            },
        )
    logger.info("Enqueued WITHDRAWAL_PROCESSED notification for user %s", user_id)


async def _send_withdrawal_processed_email(
    user_id: str,
    transaction_id: str,
    session: AsyncSession,
    amount: str = "",
    currency: str = "",
):
    """Send withdrawal processed email to the user using the provided session."""
    resend_config = ResendConfig()
    resend_service = ResendService(resend_config)
    user_repo = UserRepository(session)
    user, _ = await user_repo.find_one(id=user_id)
    if user:
        app_settings = AppSettings()
        if user.email_notifications:
            await send_transactional_email(
                resend_service=resend_service,
                to=user.email,
                subject=NotificationMessages.email_withdrawal_processed().subject,
                template_name=NotificationMessages.email_withdrawal_processed().template_name,
                app_logo_url=app_settings.logo_url,
                amount=amount,
                currency=currency.upper(),
                transaction_id=transaction_id or "",
            )


async def _process_withdrawal_task_async(
    user_id: UserId,
    withdrawal_request_data: Dict[str, Any],
    transaction_id: str,
    wallet_id: str,
    ledger_id: str,
):
    """
    Internal async task to process a withdrawal request.
    Manages a single session for the entire lifecycle.
    """
    logger.info(
        "Starting withdrawal processing task for user %s, transaction %s",
        user_id,
        transaction_id,
    )
    config = load_config()
    async for session in get_session():
        factory = TaskDependenciesFactory(session, config)
        wallet_manager_usecase = factory.get_wallet_manager_usecase(
            wallet_id, ledger_id
        )

        err = await wallet_manager_usecase.execute_withdrawal_processing(
            user_id=user_id,
            withdrawal_request_data=withdrawal_request_data,
            transaction_id=transaction_id,
        )

        if err:
            logger.error(
                "Withdrawal processing failed for user %s, transaction %s: %s",
                user_id,
                transaction_id,
                err.message,
            )
            return

        logger.info(
            "Withdrawal for user %s, transaction %s completed successfully",
            user_id,
            transaction_id,
        )

        # Notify user their withdrawal has been processed (push + email)
        await _send_withdrawal_processed_notification(
            str(user_id), str(transaction_id), session
        )
        amount = str(withdrawal_request_data.get("amount", ""))
        currency = str(withdrawal_request_data.get("currency", ""))
        await _send_withdrawal_processed_email(
            str(user_id), transaction_id, session, amount=amount, currency=currency
        )
        break


def process_withdrawal_task(
    user_id: UserId,
    withdrawal_request_data: Dict[str, Any],
    transaction_id: str,
    wallet_id: str,
    ledger_id: str,
):
    """
    RQ task to process a withdrawal request asynchronously.
    """
    asyncio.run(
        _process_withdrawal_task_async(
            user_id,
            withdrawal_request_data,
            transaction_id,
            wallet_id,
            ledger_id,
        )
    )
