"""
Shared utilities for the data sync workflow.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    """Get current time in IST timezone."""
    return datetime.now(IST)


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string, defaulting to IST if no timezone."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=IST)
    except Exception:
        return None
