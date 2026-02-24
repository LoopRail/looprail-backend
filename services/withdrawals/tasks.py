import asyncio
import logging
from typing import Any, Dict

from services.withdrawals.dependencies import get_task_wallet_manager_usecase
from src.infrastructure.db import get_session
from src.infrastructure.redis import RQManager
from src.infrastructure.repositories import SessionRepository, UserRepository
from src.infrastructure.settings import RedisConfig, ResendConfig
from src.infrastructure.services.resend_service import ResendService
from src.types.common_types import UserId
from src.types.notification_types import NotificationAction
from src.utils.email_helpers import send_transactional_email

logger = logging.getLogger(__name__)


async def _send_withdrawal_processed_notification(user_id: str, transaction_id: str):
    """
    Enqueue a WITHDRAWAL_PROCESSED push notification for the user by looking up
    their active sessions with FCM tokens directly from the DB.
    """
    try:
        redis_config = RedisConfig()
        rq_manager = RQManager(redis_config)
        from rq import Queue
        notif_queue = Queue("notifications", connection=rq_manager.get_connection())

        async for session in get_session():
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
                        "action": NotificationAction.WITHDRAWAL_PROCESSED,
                        "data": {"transaction_id": transaction_id or ""},
                        "type": "push",
                    },
                )
            logger.info("Enqueued WITHDRAWAL_PROCESSED notification for user %s", user_id)
            break
    except Exception as e:
        logger.error("Failed to send withdrawal processed notification: %s", e)


async def _send_withdrawal_processed_email(user_id: str, transaction_id: str, amount: str = "", currency: str = ""):
    """Send withdrawal processed email to the user."""
    try:
        resend_config = ResendConfig()
        resend_service = ResendService(resend_config)
        async for session in get_session():
            user_repo = UserRepository(session)
            user, _ = await user_repo.find_one(id=user_id)
            if user:
                await send_transactional_email(
                    resend_service=resend_service,
                    to=user.email,
                    subject="Your Withdrawal Has Been Processed",
                    template_name="withdrawal_processed",
                    amount=amount,
                    currency=currency,
                    transaction_id=transaction_id or "",
                )
            break
    except Exception as e:
        logger.error("Failed to send withdrawal processed email: %s", e)


async def _process_withdrawal_task_async(
    ledger_config,
    paycrest_config,
    blockrader_config,
    user_id: UserId,
    withdrawal_request_data: Dict[str, Any],
    transaction_id: str,
    wallet_name: str,
    ledger_id: str,
):
    """
    Internal async task to process a withdrawal request.
    """
    logger.info(
        "Starting withdrawal processing task for user %s, transaction %s",
        user_id,
        transaction_id,
    )
    wallet_manager_usecase = await get_task_wallet_manager_usecase(
        ledger_config, paycrest_config, blockrader_config, wallet_name, ledger_id
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
    await _send_withdrawal_processed_notification(str(user_id), transaction_id)
    amount = str(withdrawal_request_data.get("amount", ""))
    currency = str(withdrawal_request_data.get("currency", ""))
    await _send_withdrawal_processed_email(str(user_id), transaction_id, amount=amount, currency=currency)


def process_withdrawal_task(
    ledger_config,
    paycrest_config,
    blockrader_config,
    user_id: UserId,
    withdrawal_request_data: Dict[str, Any],
    transaction_id: str,
    wallet_name: str,
    ledger_id: str,
):
    """
    RQ task to process a withdrawal request asynchronously.
    """
    asyncio.run(
        _process_withdrawal_task_async(
            ledger_config,
            paycrest_config,
            blockrader_config,
            user_id,
            withdrawal_request_data,
            transaction_id,
            wallet_name,
            ledger_id,
        )
    )
