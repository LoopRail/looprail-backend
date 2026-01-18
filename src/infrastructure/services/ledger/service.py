from typing import Optional, Tuple

from src.infrastructure.logger import get_logger
from src.infrastructure.services.ledger.client import (
    BalanceManager,
    BalanceMonitorManager,
    BlnkApiKeyManager,
    BlnkGenericManager,
    BlnkHookManager,
    IdentityManager,
    LedgerManager,
    ReconciliationManager,
    TransactionManager,
)
from src.infrastructure.settings import LedgderServiceConfig
from src.types.error import Error
from src.types.ledger_types import Ledger

logger = get_logger(__name__)


class LedgerService:
    def __init__(self, config: LedgderServiceConfig):
        logger.debug("LedgerService initialized.")
        self.config = config  # Store the config for later use
        self.ledgers = LedgerManager(config)
        self.balances = BalanceManager(config)
        self.identities = IdentityManager(config)  # TODO look at tokenize
        self.transactions = TransactionManager(
            config
        )  # TODO Record bulk transaction and search
        self.balance_monitors = BalanceMonitorManager(config)
        self.reconciliation = ReconciliationManager(config)
        self.hooks = BlnkHookManager(config)
        self.api_keys = BlnkApiKeyManager(config)
        self.generic = BlnkGenericManager(config)
