from typing import List

from src.dtos.notification_dtos import PushNotificationDTO
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import SessionRepository
from src.types.notification_types import NotificationAction, NotificationType
from src.usecases.notification_usecases import NotificationUseCase

logger = get_logger(__name__)


async def enqueue_notifications_for_user(
    user_id: str,
    session_repo: SessionRepository,
    notification_usecase: NotificationUseCase,
    title: str,
    body: str,
    action: NotificationAction,
    data: dict = None,
) -> None:
    """
    Fetch all active, notifications-enabled sessions for a user and
    enqueue one push notification per FCM token.
    """
    sessions: List = await session_repo.get_user_sessions(user_id)
    tokens_notified = 0
    for session in sessions:
        if not session.allow_notifications or not session.fcm_token:
            continue
        notification = PushNotificationDTO(
            user_id=str(user_id),
            token=session.fcm_token,
            title=title,
            body=body,
            action=action,
            type=NotificationType.PUSH,
            data=data or {},
        )
        notification_usecase.enqueue_push(notification)
        tokens_notified += 1

    logger.info(
        "Enqueued '%s' push notification for user %s across %d session(s)",
        action,
        user_id,
        tokens_notified,
    )
