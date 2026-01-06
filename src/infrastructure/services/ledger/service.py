from src.infrastructure.settings import LedgderServiceConfig
from src.infrastructure.services.ledger.client import (
    LedgerManager,
    BalanceManager,
    IdentityManager,
    TransactionManager,
    BalanceMonitorManager,
    ReconciliationManager,
    BlnkHookManager,
    BlnkApiKeyManager,
    BlnkGenericManager,
)


class LedgerService:
    def __init__(self, config: LedgderServiceConfig):
        self.ledgers = LedgerManager(config)
        self.balances = BalanceManager(config)
        self.identities = IdentityManager(config) # TODO look at tokenize 
        self.transactions = TransactionManager(config) # TODO Record bulk transaction and search
        self.balance_monitors = BalanceMonitorManager(config)
        self.reconciliation = ReconciliationManager(config)
        self.hooks = BlnkHookManager(config)
        self.api_keys = BlnkApiKeyManager(config)
        self.generic = BlnkGenericManager(config)
