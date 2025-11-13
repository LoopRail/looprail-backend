from functools import wraps
from typing import Callable, Type

from src.infrastructure.db.unit_of_work import UnitOfWork
from src.types.error import Error, error


def transactional(func: Callable) -> Callable:
    """
    A decorator that wraps an asynchronous function in a database transaction
    using the UnitOfWork pattern.

    This decorator provides a transactional boundary for the decorated function.
    It ensures that all database operations within the function are executed
    as a single atomic unit. The decorated function is responsible for explicitly
    calling `uow.commit()` to finalize the transaction. If any exception occurs
    before `uow.commit()` is called, the transaction is rolled back.

    The decorated function must accept a `UnitOfWork` instance as its first
    argument (after `self` if it's a method).

    Usage:
        @transactional
        async def my_service_method(uow: UnitOfWork, arg1, arg2):
            # Database operations using uow.session
            ...
            await uow.commit() # Explicit commit

    Args:
        func: The asynchronous function to wrap in a transaction.

    Returns:
        A new asynchronous function that manages the transaction.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check if a UnitOfWork is already provided (e.g., by another transactional decorator)
        # If not, create a new UnitOfWork for this transaction.
        uow_arg_name = "uow"
        if uow_arg_name in kwargs and isinstance(kwargs[uow_arg_name], UnitOfWork):
            uow = kwargs[uow_arg_name]
            # If uow is already in kwargs, assume it's managed externally
            # and just call the function.
            return await func(*args, **kwargs)
        else:
            async with UnitOfWork() as uow:
                try:
                    result = await func(uow, *args, **kwargs)
                    # The decorated function is responsible for calling uow.commit()
                    # If it doesn't, the transaction will be rolled back on __aexit__
                    return result
                except Exception as e:
                    # The __aexit__ of UnitOfWork will handle rollback
                    raise  # Re-raise the exception after rollback

    return wrapper
