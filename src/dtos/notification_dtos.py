from typing import Any, Dict, Optional
from pydantic import Field

from src.dtos.base import Base
from src.types.notification_types import NotificationAction, NotificationType


class NotificationDTO(Base):
    user_id: str
    type: NotificationType
    title: str
    body: str
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PushNotificationDTO(NotificationDTO):
    type: NotificationType = NotificationType.PUSH
    token: str
    action: NotificationAction = NotificationAction.NONE
    image_url: Optional[str] = None
    priority: Optional[str] = "high"
    channel_id: Optional[str] = "default"
    icon: Optional[str] = "ic_notification"
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None



