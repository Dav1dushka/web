from calendar import monthrange
from datetime import datetime, timedelta


def next_occurrence(dt: datetime, repeat: str) -> datetime | None:
    if repeat == "once":
        return None

    if repeat == "daily":
        return dt + timedelta(days=1)

    if repeat == "2d":
        return dt + timedelta(days=2)

    if repeat == "week":
        return dt + timedelta(days=7)

    if repeat.startswith("weekly:"):
        days = {
            int(value)
            for value in repeat.split(":", 1)[1].split(",")
            if value
        }
        candidate = dt + timedelta(days=1)

        for _ in range(14):
            if candidate.weekday() in days:
                return candidate
            candidate += timedelta(days=1)

        return dt + timedelta(days=7)

    if repeat == "month":
        month = 1 if dt.month == 12 else dt.month + 1
        year = dt.year + 1 if dt.month == 12 else dt.year
        day = min(dt.day, monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    if repeat == "year":
        day = 28 if dt.month == 2 and dt.day == 29 else dt.day
        return dt.replace(year=dt.year + 1, day=day)

    return None
