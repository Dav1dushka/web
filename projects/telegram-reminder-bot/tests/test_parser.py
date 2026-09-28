from datetime import datetime

from app.recurrence import next_occurrence


def test_daily_repeat():
    value = datetime(2026, 10, 27, 9, 0)

    assert next_occurrence(value, "daily").day == 28


def test_every_two_days():
    value = datetime(2026, 10, 27, 9, 0)

    assert next_occurrence(value, "2d").day == 29


def test_custom_weekdays():
    value = datetime(2026, 10, 27, 9, 0)
    result = next_occurrence(value, "weekly:0,2,4")

    assert result.weekday() == 2
