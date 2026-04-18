from enum import Enum
from typing import NamedTuple, Tuple


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

    # Auth lifecycle
    LOGIN_ALERT = "LOGIN_ALERT"
    PASSWORD_RESET = "PASSWORD_RESET"
    WELCOME = "WELCOME"

    # Generic fallback
    NONE = "NONE"


class EmailMessage(NamedTuple):
    subject: str
    template_name: str


class PushMessage(NamedTuple):
    title: str
    body: str


class NotificationMessages:
    # ── Push ────────────────────────────────────────────────────────────────

    @staticmethod
    def deposit_confirmed(amount: str, currency: str) -> PushMessage:
        return PushMessage(
            title="Deposit Confirmed ✅",
            body=f"Your deposit of {amount} {currency} has been confirmed and added to your wallet.",
        )

    @staticmethod
    def withdrawal_initiated() -> PushMessage:
        return PushMessage(
            title="Withdrawal Initiated",
            body="Your withdrawal is being processed.",
        )

    @staticmethod
    def withdrawal_confirmed(recipient_name: str) -> PushMessage:
        return PushMessage(
            title="Funds Delivered",
            body=f"Your transfer to {recipient_name} has been completed successfully.",
        )

    # ── Email ────────────────────────────────────────────────────────────────

    @staticmethod
    def email_login_alert() -> EmailMessage:
        return EmailMessage(
            subject="New Login to Your LoopRail Account",
            template_name="login_alert",
        )

    @staticmethod
    def email_password_reset() -> EmailMessage:
        return EmailMessage(
            subject="Reset Your LoopRail Password",
            template_name="password_reset_otp",
        )

    @staticmethod
    def email_deposit_confirmed() -> EmailMessage:
        return EmailMessage(
            subject="Your Deposit Has Been Confirmed",
            template_name="deposit_confirmed",
        )

    @staticmethod
    def email_withdrawal_processed() -> EmailMessage:
        return EmailMessage(
            subject="Your Withdrawal Has Been Processed",
            template_name="withdrawal_processed",
        )

    @staticmethod
    def email_welcome() -> EmailMessage:
        return EmailMessage(
            subject="Welcome to LoopRail 🎉",
            template_name="welcome",
        )
