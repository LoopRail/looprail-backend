"""
Send a real WITHDRAWAL_PROCESSED push notification to a device for manual testing.

Usage:
    uv run python scripts/send_test_withdrawal_notification.py <fcm_token>
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.notifications.service import NotificationService
from src.dtos.notification_dtos import PushNotificationDTO
from src.infrastructure.services import ResendService
from src.infrastructure.settings import ENVIRONMENT, FirebaseConfig, ResendConfig
from src.types.notification_types import NotificationAction, NotificationType


async def main(fcm_token: str):
    firebase_config = FirebaseConfig()
    firebase_config.environment = ENVIRONMENT.PRODUCTION
    resend_service = ResendService(config=ResendConfig())
    service = NotificationService(
        resend_service=resend_service, firebase_config=firebase_config
    )
    notification = PushNotificationDTO(
        user_id="test-user",
        token=fcm_token,
        title="Withdrawal Processed ✅",
        body="Your withdrawal has been successfully processed.",
        action=NotificationAction.WITHDRAWAL_PROCESSED,
        type=NotificationType.PUSH,
        data={"transaction_id": "test-txn-001"},
    )

    success, error = await service.send_push(notification)
    if success:
        print("✅ Notification sent successfully.")
    else:
        print(f"❌ Failed to send notification: {error}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: uv run python scripts/send_test_withdrawal_notification.py <fcm_token>"
        )
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
