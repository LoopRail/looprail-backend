import asyncio
from typing import Any, Dict

from src.dtos.notification_dtos import PushNotificationDTO
from src.infrastructure.logger import get_logger
from services.notifications.service import NotificationService
from src.infrastructure.services.resend_service import ResendService
from src.infrastructure.settings import ResendConfig, AppSettings, FirebaseConfig

logger = get_logger(__name__)

# Initialize service
resend_config = ResendConfig()
firebase_config = FirebaseConfig()
app_settings = AppSettings()
resend_service = ResendService(resend_config, environment=app_settings.environment)
notification_service = NotificationService(
    resend_service, 
    firebase_config, 
    environment=app_settings.environment,
    app_logo_url=app_settings.logo_url
)


def send_push_notification_task(notification_data: Dict[str, Any]):
    """Background task to send push notification."""
    notification = PushNotificationDTO(**notification_data)
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        future = asyncio.ensure_future(notification_service.send_push(notification))
        return future
    else:
        return loop.run_until_complete(notification_service.send_push(notification))


