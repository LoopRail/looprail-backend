import os
from typing import Optional, Tuple

from src.dtos.notification_dtos import EmailNotificationDTO, PushNotificationDTO
from src.infrastructure.logger import get_logger
from src.infrastructure.services.resend_service import ResendService
from src.types import Error
from src.utils import load_html_template

logger = get_logger(__name__)


class NotificationService:
    def __init__(self, resend_service: ResendService):
        self.resend_service = resend_service

    async def send_push(self, notification: PushNotificationDTO) -> Tuple[bool, Optional[Error]]:
        # TODO: Implement actual FCM or Expo logic here
        logger.info(f"Sending push notification to {notification.token}: {notification.title}")
        return True, None

    async def send_email(self, notification: EmailNotificationDTO) -> Tuple[bool, Optional[Error]]:
        logger.info(f"Sending email notification to {notification.email}: {notification.subject}")
        
        html_content = None
        if notification.template_name:
            html_content, err = load_html_template(
                notification.template_name, **notification.template_data
            )
            if err:
                return False, err
        
        # If no template, use body as content
        if not html_content:
            html_content = f"<p>{notification.body}</p>"

        response, err = await self.resend_service.send(
            to=notification.email,
            _from=os.getenv("SENDER_EMAIL", "notifications@looprail.com"),
            subject=notification.subject or notification.title,
            html_content=html_content,
            text_content=notification.body
        )
        
        if err:
            return False, err
        
        return True, None
