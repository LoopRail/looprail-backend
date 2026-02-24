from rq import Queue
from src.dtos.notification_dtos import PushNotificationDTO


class NotificationUseCase:
    def __init__(self, queue: Queue):
        self.queue = queue

    def enqueue_push(self, notification: PushNotificationDTO):
        """Enqueues a push notification task."""
        self.queue.enqueue(
            "services.notifications.tasks.send_push_notification_task",
            notification.model_dump(),
            job_id=f"push_{notification.user_id}_{notification.type}",
        )

