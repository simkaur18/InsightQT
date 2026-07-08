import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TypeVar

from app.utils.constants import DATE_RANGE_PRESETS

T = TypeVar("T")


def resolve_date_range_since(preset: str) -> datetime | None:
    """Convert a DATE_RANGE_PRESETS label into a cutoff datetime.

    Returns None for "All time" (or any unrecognized preset), meaning no
    date filtering should be applied.
    """
    days = DATE_RANGE_PRESETS.get(preset)
    if days is None:
        return None
    return datetime.now() - timedelta(days=days)


def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int,
    base_delay_seconds: float = 1.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Call func(), retrying with exponential backoff on the given exception types.

    Re-raises the last exception if all retries are exhausted.
    """
    last_exception: Exception | None = None
    for attempt in range(max_retries):
        try:
            return func()
        except retry_on as exc:
            last_exception = exc
            if attempt < max_retries - 1:
                time.sleep(base_delay_seconds * (2**attempt))
    assert last_exception is not None
    raise last_exception
