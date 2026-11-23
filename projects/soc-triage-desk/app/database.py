from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "soc_triage.db"


def get_db_path() -> Path:
    return Path(os.getenv("SOC_TRIAGE_DB", str(DEFAULT_DB)))


@contextmanager
def connect():
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                total_lines INTEGER NOT NULL,
                parsed_events INTEGER NOT NULL,
                incidents INTEGER NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )


def save_analysis(source_name: str, result: dict) -> int:
    summary = result["summary"]
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO analyses(source_name, total_lines, parsed_events, incidents, result_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                source_name[:120],
                summary["total_lines"],
                summary["parsed_events"],
                summary["incidents"],
                json.dumps(result, ensure_ascii=False),
            ),
        )
        return int(cursor.lastrowid)


def get_history(limit: int = 20) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, source_name, created_at, total_lines, parsed_events, incidents
            FROM analyses ORDER BY id DESC LIMIT ?
            """,
            (max(1, min(limit, 100)),),
        ).fetchall()
    return [dict(row) for row in rows]


def get_analysis(analysis_id: int) -> dict | None:
    with connect() as connection:
        row = connection.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["result"] = json.loads(item.pop("result_json"))
    return item
