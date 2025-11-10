import logging
from functools import wraps
from typing import TypeVar
from collections.abc import Callable

from fastapi import HTTPException

from matching_service.utils.exceptions import (
    DomainError,
    EmptyStorageError,
    InvalidTextError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _map_exception_to_response(exception: Exception) -> tuple[int, str, str]:
    if isinstance(exception, EmptyStorageError):
        return 404, "Empty storage", str(exception)
    if isinstance(exception, (InvalidTextError, ValueError)):
        return 400, "Validation error", str(exception)
    if isinstance(exception, DomainError):
        return 400, "Domain error", str(exception)
    if isinstance(exception, RuntimeError):
        return 500, "Runtime error", "Service unavailable"
    return 500, "Error", "Internal error"


def handle_service_errors(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            status_code, log_message, detail = _map_exception_to_response(e)

            if status_code >= 500:
                logger.error("%s: %s", log_message, e, exc_info=True)
            else:
                logger.warning("%s: %s", log_message, e)

            raise HTTPException(status_code=status_code, detail=detail)

    return wrapper
