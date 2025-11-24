from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.settings import database_config

engine = create_async_engine(database_config.get_uri(), echo=True)


async def get_session() -> Optional[AsyncSession]:
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        try:
            async with session.begin():
                yield session
        except SQLAlchemyError:
            session.rollback()
            yield session

        finally:
            session.commit()
            session.close()
