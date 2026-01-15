import logging
from typing import Any, Dict

from src.infrastructure.factories import get_wallet_manager_usecase_for_task
from src.types.common_types import UserId

logger = logging.getLogger(__name__)


def process_withdrawal_task(
    user_id: UserId,
    withdrawal_request_data: Dict[str, Any],
    pin: str,
    transaction_id: str,
):
    """
    RQ task to process a withdrawal request asynchronously.
    """
    logger.info("Starting withdrawal processing task for user %s, transaction %s", user_id, transaction_id)
    try:
        wallet_manager_usecase = get_wallet_manager_usecase_for_task()
        err = wallet_manager_usecase.execute_withdrawal_processing(
            user_id=user_id,
            withdrawal_request_data=withdrawal_request_data,
            pin=pin,
            transaction_id=transaction_id,
        )
        if err:
            logger.error(
                "Withdrawal processing failed for user %s, transaction %s: %s",
                user_id,
                transaction_id,
                err.message,
            )
        else:
            logger.info("Withdrawal for user %s, transaction %s completed successfully", user_id, transaction_id)
    except Exception as e:
        logger.exception(
            "An unexpected error occurred during withdrawal processing for user %s, transaction %s",
            user_id,
            transaction_id,
        )
