from rq import Worker, Queue
from src.infrastructure.logger import get_logger
from src.infrastructure.redis import RQManager
from src.infrastructure.settings import RedisConfig

logger = get_logger(__name__)


def run_notification_worker():
    redis_config = RedisConfig()
    rq_manager = RQManager(redis_config)
    
    # We can use a specific 'notifications' queue
    notification_queue = Queue('notifications', connection=rq_manager.get_connection())
    
    worker = Worker([notification_queue], connection=rq_manager.get_connection())
    logger.info("Notification worker started, listening on 'notifications' queue")
    worker.work()


if __name__ == "__main__":
    run_notification_worker()
