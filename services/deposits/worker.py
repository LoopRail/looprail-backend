from rq import Queue, Worker

from src.infrastructure.logger import get_logger
from src.infrastructure.redis import RQManager
from src.infrastructure.settings import RedisConfig

logger = get_logger(__name__)


def run_worker():
    redis_config = RedisConfig()
    rq_manager = RQManager(redis_config)
    queue = Queue("deposits", connection=rq_manager.get_connection())
    worker = Worker([queue], connection=rq_manager.get_connection())
    worker.work()


if __name__ == "__main__":
    logger.info("Starting RQ worker...")
    run_worker()
