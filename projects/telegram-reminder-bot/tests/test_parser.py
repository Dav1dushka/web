import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot import parse_reminder


def test_parse_one_time_reminder():
    reminder_at, title, repeat = parse_reminder(
        "2026-10-27 09:00 | Mom's birthday"
    )

    assert reminder_at.strftime("%Y-%m-%d %H:%M") == "2026-10-27 09:00"
    assert title == "Mom's birthday"
    assert repeat == "none"


def test_parse_yearly_reminder():
    _, _, repeat = parse_reminder(
        "2026-10-27 09:00 | Mom's birthday | yearly"
    )

    assert repeat == "yearly"
