from enum import Enum
from typing import Tuple


class NotificationType(str, Enum):
    PUSH = "push"


class NotificationAction(str, Enum):
    # Deposit lifecycle
    DEPOSIT_RECEIVED = "DEPOSIT_RECEIVED"  # deposit hit the chain, pending sweep
    DEPOSIT_CONFIRMED = "DEPOSIT_CONFIRMED"  # deposit swept and balance updated

    # Withdrawal lifecycle
    WITHDRAWAL_INITIATED = "WITHDRAWAL_INITIATED"  # withdrawal enqueued by user
    WITHDRAWAL_PROCESSED = "WITHDRAWAL_PROCESSED"  # withdrawal executed by worker
    WITHDRAWAL_CONFIRMED = (
        "WITHDRAWAL_CONFIRMED"  # withdrawal swept and balance updated
    )

    # Generic fallback
    NONE = "NONE"


class NotificationMessages:
    @staticmethod
    def deposit_confirmed(amount: str, currency: str) -> Tuple[str, str]:
        return (
            "Deposit Confirmed ✅",
            f"Your deposit of {amount} {currency} has been confirmed and added to your wallet.",
        )

    @staticmethod
    def withdrawal_initiated() -> Tuple[str, str]:
        return ("Withdrawal initiated", "Your withdrawal is being processed.")

    @staticmethod
    def withdrawal_confirmed(recipient_name: str) -> Tuple[str, str]:
        return (
            "Funds Delivered",
            f"Your transfer to {recipient_name} has been completed successfully.",
        )
