from typing import Callable, Dict, Optional, TYPE_CHECKING

from src.types.error import Error
from src.types.types import WithdrawalMethod

if TYPE_CHECKING:
    from src.dtos.wallet_dtos import (
        BankTransferData,
        ExternalWalletTransferData,
        WithdrawalRequest,
    )
    from src.dtos.transaction_dtos import CreateTransactionParams
    from src.models import Asset, User, Transaction
    from src.usecases.wallet_usecases import WalletManagerUsecase

# Define a type hint for the withdrawal handler functions
WithdrawalHandler = Callable[
    [
        "WalletManagerUsecase",
        "User",
        "WithdrawalRequest",
        "BankTransferData | ExternalWalletTransferData",  # Specific data type
        "Asset",
        "CreateTransactionParams",  # Partially filled transaction params
    ],
    "tuple[Optional[Transaction], Optional[Error]]",  # Returns created Transaction or Error
]


class WithdrawalHandlerRegistry:
    _handlers: Dict[WithdrawalMethod, WithdrawalHandler] = {}

    @classmethod
    def register_handler(
        cls, method: WithdrawalMethod
    ) -> Callable[[WithdrawalHandler], WithdrawalHandler]:
        def decorator(handler: WithdrawalHandler) -> WithdrawalHandler:
            if method in cls._handlers:
                if (
                    cls._handlers[method] != handler
                ):  # Allow re-registration of the same handler for hot reloading/testing
                    raise ValueError(
                        f"Handler for withdrawal method {method.value} already registered with a different handler."
                    )
            cls._handlers[method] = handler
            return handler

        return decorator

    @classmethod
    def get_handler(cls, method: WithdrawalMethod) -> Optional[WithdrawalHandler]:
        return cls._handlers.get(method)

    @classmethod
    def list_handlers(cls) -> Dict[WithdrawalMethod, WithdrawalHandler]:
        return cls._handlers
