from typing import Callable, Dict

from src.types.types import WithdrawalMethod

WITHDRAWAL_HANDLERS: Dict[WithdrawalMethod, Callable] = {}


def register_withdrawal_handler(method: WithdrawalMethod):
    def decorator(func: Callable):
        if method in WITHDRAWAL_HANDLERS:
            raise ValueError(
                f"Withdrawal handler for method {method} already registered."
            )
        WITHDRAWAL_HANDLERS[method] = func
        return func

    return decorator


def get_withdrawal_handler(method: WithdrawalMethod) -> Callable:
    handler = WITHDRAWAL_HANDLERS.get(method)
    if not handler:
        raise ValueError(f"No withdrawal handler registered for method {method}.")
    return handler
