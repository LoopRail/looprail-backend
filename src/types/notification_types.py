from enum import Enum
from typing import NewType


NotificationId = NewType("NotificationId", str)
NotificationToken = NewType("NotificationToken", str)


class NotificationProvider(str, Enum):
    FCM = "fcm"
    SES = "ses"  # Assuming AWS SES for email, or generic
    SMTP = "smtp"


class NotificationType(str, Enum):
    PUSH = "push"
    EMAIL = "email"
