from enum import Enum


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
