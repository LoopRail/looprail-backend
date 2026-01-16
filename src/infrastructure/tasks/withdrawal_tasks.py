import logging
from typing import Any, Dict

from src.infrastructure.config_settings import Config
from src.infrastructure.tasks.dependencies import \
    get_task_wallet_manager_usecase
from src.types.common_types import UserId

logger = logging.getLogger(__name__)


def process_withdrawal_task(
    config: Config,
    user_id: UserId,
    withdrawal_request_data: Dict[str, Any],
    pin: str,
    transaction_id: str,
):
    """
    RQ task to process a withdrawal request asynchronously.
    """
    logger.info(
        "Starting withdrawal processing task for user %s, transaction %s",
        user_id,
        transaction_id,
    )
    wallet_name = withdrawal_request_data["wallet_name"]
    ledger_id = withdrawal_request_data["ledger_id"]
    wallet_manager_usecase = get_task_wallet_manager_usecase(
        config, wallet_name, ledger_id
    )
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
        return
    logger.info(
        "Withdrawal for user %s, transaction %s completed successfully",
        user_id,
        transaction_id,
    )
    return
