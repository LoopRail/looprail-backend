import os
import firebase_admin
from firebase_admin import credentials, messaging
from typing import Optional, Tuple

from src.dtos.notification_dtos import PushNotificationDTO
from src.infrastructure.logger import get_logger
from src.infrastructure.services.resend_service import ResendService
from src.infrastructure.settings import FirebaseConfig
from src.types import Error
from src.utils import load_html_template

logger = get_logger(__name__)


class NotificationService:
    def __init__(self, resend_service: ResendService, firebase_config: FirebaseConfig):
        self.resend_service = resend_service
        self.firebase_config = firebase_config
        self._initialize_firebase()

    def _initialize_firebase(self):
        try:
            # Check if app is already initialized
            firebase_admin.get_app()
        except ValueError:
            # Construct credentials from config
            if self.firebase_config.firebase_project_id:
                cred_dict = {
                    "type": "service_account",
                    "project_id": self.firebase_config.firebase_project_id,
                    "private_key": self.firebase_config.firebase_private_key.replace(
                        "\\n", "\n"
                    )
                    if self.firebase_config.firebase_private_key
                    else None,
                    "client_email": self.firebase_config.firebase_client_email,
                }
                # Filter out None values
                cred_dict = {k: v for k, v in cred_dict.items() if v is not None}
                
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(
                    cred, {"databaseURL": self.firebase_config.firebase_database_url}
                )
                logger.info("Firebase app initialized successfully")
            else:
                logger.warning("Firebase config missing project_id, skipping initialization")

    async def send_push(self, notification: PushNotificationDTO) -> Tuple[bool, Optional[Error]]:
        logger.info(f"Sending push notification to {notification.token}: {notification.title}")
                
        message = messaging.Message(
            token=notification.token,
            notification=messaging.Notification(
                title=notification.title,
                body=notification.body,
                image=notification.image_url,
            ),
            data={
                **(notification.data or {}),
                'action': notification.action,
                'campaign_id': str(notification.campaign_id) if notification.campaign_id else '',
                'campaign_name': notification.campaign_name or '',
            },
            android=messaging.AndroidConfig(
                priority=notification.priority,
                notification=messaging.AndroidNotification(
                    channel_id=notification.channel_id,
                    sound='default',
                    click_action='android.intent.action.VIEW',
                    icon=notification.icon,
                    color='#4CAF50',
                    image=notification.image_url,
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1,
                        mutable_content=True,
                    )
                ),
                fcm_options=messaging.APNSFCMOptions(
                    image=notification.image_url,
                ) if notification.image_url else None,
            ),
            fcm_options=messaging.FCMOptions(
                analytics_label=notification.campaign_name or 'default',
            ),
        )

        try:
            response = messaging.send(message)
            logger.info(f"Successfully sent message: {response}")
            return True, None
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            from src.types import InternalError
            return False, InternalError(message=str(e))

