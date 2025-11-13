from typing import Callable, Optional, Tuple, TypeVar

from sqlmodel.ext.asyncio.session import AsyncSession

from src.types.error import Error, error

T = TypeVar("T")


class BaseRepository:
    """
    Base class for repositories to provide common functionality like session management
    and transaction handling.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _execute_in_transaction(
        self, func: Callable[..., Tuple[Optional[T], Error]], *args, **kwargs
    ) -> Tuple[Optional[T], Error]:
        """
        Executes a given function within a database transaction.

        Args:
            func: The asynchronous function to execute.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            A tuple containing the result of the function and an error, if any.
        """
        try:
            async with self.session.begin():
                result, err = await func(self.session, *args, **kwargs)
                if err:
                    await self.session.rollback()
                    return None, err
                await self.session.commit()
                return result, None
        except Exception as e:
            await self.session.rollback()
            return None, error(str(e))
