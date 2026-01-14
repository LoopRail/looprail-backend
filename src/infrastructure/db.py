from typing import AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.ext.asyncio.engine import AsyncEngine

from src.infrastructure import get_logger, load_config
from src.types import InternaleServerError

db_url = load_config().database.get_uri()

logger = get_logger(__name__)


def get_engine(db_uri: str) -> AsyncEngine:
    engine = create_async_engine(db_uri) # TODO do not echo in prod
    return engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine(db_url)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            async with session.begin():
                logger.info("Database session")
                yield session
        except ConnectionRefusedError as e:
            logger.error(
                "Database session error: %s, connection refused", e, exc_info=True
            )

            raise InternaleServerError from e

        except SQLAlchemyError as e:
            logger.error("Database session error: %s", e, exc_info=True)
            await session.rollback()
            raise InternaleServerError from e
        finally:
            if session.is_active:
                try:
                    await session.flush()
                    await session.commit()
                except SQLAlchemyError as e:
                    logger.error(
                        "Failed to flush/commit in finally: %s", e, exc_info=True
                    )
                    await session.rollback()
            await session.close()
