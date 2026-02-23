import asyncio
import logging
from typing import Any, Dict

from src.infrastructure.tasks.dependencies import get_task_wallet_manager_usecase
from src.types.common_types import UserId

logger = logging.getLogger(__name__)


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
