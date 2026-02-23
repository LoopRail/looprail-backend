from typing import Any, Dict, Optional
from pydantic import Field

from src.dtos.base import Base
from src.types.notification_types import NotificationType


class NotificationDTO(Base):
    user_id: str
    type: NotificationType
    title: str
    body: str
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PushNotificationDTO(NotificationDTO):
    type: NotificationType = NotificationType.PUSH
    token: str


class EmailNotificationDTO(NotificationDTO):
    type: NotificationType = NotificationType.EMAIL
    email: str
    subject: Optional[str] = None
    template_name: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
