import asyncio
import sys
import argparse
from src.infrastructure.settings import FirebaseConfig, AppSettings, ENVIRONMENT, ResendConfig
from src.infrastructure.services.resend_service import ResendService
from services.notifications.service import NotificationService
from src.dtos.notification_dtos import PushNotificationDTO
from src.types.notification_types import NotificationAction, NotificationType

async def main():
    parser = argparse.ArgumentParser(description="Send a test push notification")
    parser.add_argument("--token", required=True, help="FCM token to send notification to")
    parser.add_argument("--title", default="Test Notification", help="Notification title")
    parser.add_argument("--body", default="This is a test notification from LoopRail", help="Notification body")
    args = parser.parse_args()

    firebase_config = FirebaseConfig()
    app_settings = AppSettings()
    resend_config = ResendConfig()
    
    print(f"Loading env from: {app_settings.get_env_file_path}")
    print(f"Project ID: {firebase_config.firebase_project_id}")
    print(f"Private Key ID: {firebase_config.firebase_private_key_id}")
    has_key = "PRESENT" if firebase_config.firebase_private_key else "MISSING"
    print(f"Private Key: {has_key}")
    print(f"Client Email: {firebase_config.firebase_client_email}")
    resend_service = ResendService(resend_config, environment=app_settings.environment)
    
    # Force environment to STAGING to bypass the DEVELOPMENT check in NotificationService
    service = NotificationService(
        resend_service=resend_service,
        firebase_config=firebase_config,
        environment=ENVIRONMENT.STAGING,
        app_logo_url=app_settings.logo_url
    )

    notification = PushNotificationDTO(
        user_id="test_user",
        token=args.token,
        title=args.title,
        body=args.body,
        action=NotificationAction.NONE,
        type=NotificationType.PUSH,
    )

    print(f"Sending push notification to {args.token}...")
    success, error = await service.send_push(notification)
    
    if success:
        print("Successfully sent push notification!")
    else:
        print(f"Failed to send push notification: {error}")

if __name__ == "__main__":
    asyncio.run(main())
