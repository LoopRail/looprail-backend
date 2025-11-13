from functools import wraps
from typing import Callable, Type

from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.db import session_factory
from src.types.error import Error, error


def transactional(func: Callable) -> Callable:
    """
    A decorator that wraps an asynchronous function in a database transaction.

    This decorator provides a transactional boundary for the decorated function.
    It ensures that all database operations within the function are executed
    as a single atomic unit. If the function completes successfully, the
    transaction is committed. If any exception occurs, the transaction is
    rolled back.

    The decorated function must accept an `AsyncSession` instance as its first
    argument (after `self` if it's a method).

    Usage:
        @transactional
        async def my_service_method(session: AsyncSession, arg1, arg2):
            # Database operations using the provided session
            ...

    Args:
        func: The asynchronous function to wrap in a transaction.

    Returns:
        A new asynchronous function that manages the transaction.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check if a session is already provided (e.g., by another transactional decorator)
        # If not, create a new session for this transaction.
        session_arg_name = "session"
        if session_arg_name in kwargs and isinstance(kwargs[session_arg_name], AsyncSession):
            session = kwargs[session_arg_name]
            # If session is already in kwargs, assume it's managed externally
            # and just call the function.
            return await func(*args, **kwargs)
        else:
            async with session_factory() as session:
                try:
                    result = await func(session, *args, **kwargs)
                    await session.commit()
                    return result
                except Exception as e:
                    await session.rollback()
                    raise  # Re-raise the exception after rollback

    return wrapper
