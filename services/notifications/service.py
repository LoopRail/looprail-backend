import os
import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError
from typing import Optional, Tuple

from src.dtos.notification_dtos import PushNotificationDTO
from src.infrastructure.logger import get_logger
from src.infrastructure.services.resend_service import ResendService
from src.infrastructure.settings import FirebaseConfig, ENVIRONMENT
from src.types import Error, InternaleServerError
from src.utils import load_html_template

logger = get_logger(__name__)


class NotificationService:
    def __init__(
        self,
        resend_service: ResendService,
        firebase_config: FirebaseConfig,
        environment: ENVIRONMENT | None = None,
        app_logo_url: str | None = None,
    ) -> None:
        """Initializes the NotificationService.

        Args:
            resend_service: The Resend service.
            firebase_config: The Firebase configuration.
            environment: The application environment. If not provided, it will be taken from the config.
            app_logo_url: The URL of the application logo.
        """
        self.resend_service = resend_service
        self.firebase_config = firebase_config
        self.environment = environment or firebase_config.environment
        self.app_logo_url = app_logo_url
        self._initialize_firebase()
        logger.debug("NotificationService initialized in %s environment.", self.environment.value)

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
                    "client_id": self.firebase_config.firebase_client_id,
                    "private_key_id": self.firebase_config.firebase_private_key_id,
                    "private_key": self.firebase_config.firebase_private_key.replace(
                        "\\n", "\n"
                    )
                    if self.firebase_config.firebase_private_key
                    else None,
                    "client_email": self.firebase_config.firebase_client_email,
                    "client_x509_cert_url": self.firebase_config.firebase_client_x509_cert_url,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                }
                # Filter out None values
                cred_dict = {k: v for k, v in cred_dict.items() if v is not None}
                
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
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
                image=notification.image_url or self.app_logo_url,
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
                    image=notification.image_url or self.app_logo_url,
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
                    image=notification.image_url or self.app_logo_url,
                ) if (notification.image_url or self.app_logo_url) else None,
            ),
            fcm_options=messaging.FCMOptions(
                analytics_label=notification.campaign_name or 'default',
            )
        )

        from src.infrastructure.config_settings import load_config
        config = load_config()
        if self.environment == ENVIRONMENT.DEVELOPMENT or not config.app.enable_notifications:
            logger.info(
                "Skipping push notification send. Environment: %s, Notifications Enabled: %s. Token: %s, Title: %s",
                self.environment.value,
                config.app.enable_notifications,
                notification.token,
                notification.title,
            )
            return True, None

        try:
            response = messaging.send(message)
            logger.info(f"Successfully sent message: {response}")
            return True, None
        except FirebaseError as e:
            logger.error(f"Failed to send push notification: {e}")
            return False, InternaleServerError

