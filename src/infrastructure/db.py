from typing import AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine

from src.infrastructure import get_logger, load_config
from src.infrastructure.settings import ENVIRONMENT
from src.types import InternaleServerError

config = load_config()
db_url = config.database.get_uri()

logger = get_logger(__name__)


def get_engine(db_uri: str) -> AsyncEngine:
    is_production = config.app.environment == ENVIRONMENT.PRODUCTION
    engine = create_async_engine(db_uri, echo=not is_production)
    return engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine(db_url)
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.debug("Creating database session")

    async with async_session() as session:
        try:
            logger.debug("Database session opened: %s", id(session))
            await session.begin()
            yield session
            await session.commit()
        except ConnectionRefusedError as e:
            logger.error(
                "Database connection refused (session=%s)",
                id(session),
                exc_info=True,
            )
            await session.rollback()  # Rollback on error
            raise InternaleServerError from e
        except SQLAlchemyError as e:
            logger.error(
                "SQLAlchemy error during session usage (session=%s)",
                id(session),
                exc_info=True,
            )
            await session.rollback()
            raise InternaleServerError from e
        finally:
            logger.debug(
                "Database session closed (session=%s, in_transaction=%s)",
                id(session),
                session.in_transaction(),
            )
