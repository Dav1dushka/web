from collections import Counter
from datetime import datetime
import re
import sqlite3

from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="Mini SIEM")
DB_NAME = "siem.db"

FAILED_LOGIN_RE = re.compile(
    r"^(?P<time>\S+) FAILED_LOGIN ip=(?P<ip>\S+) user=(?P<user>\S+)$"
)


def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TEXT NOT NULL,
            event_type TEXT NOT NULL,
            source_ip TEXT NOT NULL,
            username TEXT,
            raw TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            rule TEXT NOT NULL,
            source_ip TEXT NOT NULL,
            details TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def ingest_line(line: str):
    match = FAILED_LOGIN_RE.match(line.strip())

    if not match:
        return False

    conn = db()

    conn.execute(
        """
        INSERT INTO events (
            event_time,
            event_type,
            source_ip,
            username,
            raw
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            match.group("time"),
            "FAILED_LOGIN",
            match.group("ip"),
            match.group("user"),
            line.strip(),
        ),
    )

    conn.commit()
    conn.close()

    return True


def detect_bruteforce(threshold: int = 5):
    conn = db()

    rows = conn.execute(
        """
        SELECT source_ip, COUNT(*) AS failures
        FROM events
        WHERE event_type = 'FAILED_LOGIN'
        GROUP BY source_ip
        HAVING COUNT(*) >= ?
        """,
        (threshold,),
    ).fetchall()

    created = 0

    for row in rows:
        existing = conn.execute(
            """
            SELECT 1
            FROM alerts
            WHERE source_ip = ? AND rule = ?
            LIMIT 1
            """,
            (row["source_ip"], "FAILED_LOGIN_THRESHOLD"),
        ).fetchone()

        if existing:
            continue

        conn.execute(
            """
            INSERT INTO alerts (
                created_at,
                rule,
                source_ip,
                details
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(timespec="seconds"),
                "FAILED_LOGIN_THRESHOLD",
                row["source_ip"],
                f'{row["failures"]} failed login attempts',
            ),
        )

        created += 1

    conn.commit()
    conn.close()

    return created


init_db()


@app.get("/events")
def get_events(limit: int = Query(default=100, ge=1, le=500)):
    conn = db()

    rows = conn.execute(
        """
        SELECT id, event_time, event_type, source_ip, username
        FROM events
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@app.get("/alerts")
def get_alerts():
    conn = db()

    rows = conn.execute(
        """
        SELECT id, created_at, rule, source_ip, details
        FROM alerts
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@app.post("/ingest")
def ingest(log_line: str):
    if not ingest_line(log_line):
        raise HTTPException(
            status_code=400,
            detail="Unsupported log format",
        )

    created = detect_bruteforce()

    return {
        "accepted": True,
        "new_alerts": created,
    }


@app.get("/summary")
def summary():
    conn = db()

    event_count = conn.execute(
        "SELECT COUNT(*) AS count FROM events"
    ).fetchone()["count"]

    alert_count = conn.execute(
        "SELECT COUNT(*) AS count FROM alerts"
    ).fetchone()["count"]

    top_ips = conn.execute(
        """
        SELECT source_ip, COUNT(*) AS failures
        FROM events
        WHERE event_type = 'FAILED_LOGIN'
        GROUP BY source_ip
        ORDER BY failures DESC
        LIMIT 10
        """
    ).fetchall()

    conn.close()

    return {
        "events": event_count,
        "alerts": alert_count,
        "top_failed_login_ips": [dict(row) for row in top_ips],
    }
