from bot import parse_datetime


def test_parse_datetime():
    value = parse_datetime("27.10.2026 09:00")

    assert value.year == 2026
    assert value.month == 10
    assert value.day == 27
    assert value.hour == 9
    assert value.minute == 0
