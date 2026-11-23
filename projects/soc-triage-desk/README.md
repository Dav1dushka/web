# SOC Triage Desk

A local defensive-security learning platform for parsing Linux SSH / authentication logs, normalising events and surfacing explainable incident leads.

This project analyses supplied log text only. It does not connect to remote systems, execute commands, scan networks or prove that a host is compromised. Detection results are heuristic leads for analyst review.

## Features

- Parse SSH failed-login, successful-login, invalid-user and sudo events.
- Normalise events into timestamp, host, event type, username, source IP and raw evidence.
- Detect repeated failed authentication, possible password spraying, invalid-user probing, successful login after prior failures, and privileged sudo commands.
- Assign transparent severity labels and retain evidence lines for alerts.
- Store analysis history in SQLite.
- Provide a FastAPI backend, OpenAPI documentation and a responsive analyst dashboard.
- Include sample logs and automated tests.

## Tech stack

Python 3.12 · FastAPI · Pydantic · SQLite · JavaScript · HTML · CSS · pytest · Docker

## Quick start

~~~bash
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
~~~

Open http://127.0.0.1:8000 and API docs at http://127.0.0.1:8000/docs.

Run tests:

~~~bash
pytest -q
~~~

## Demo

Use Load sample in the dashboard or paste sample_logs/authentication.log. The demo includes repeated failed SSH logins, multiple usernames, a later successful login from the same source, a sudo command and invalid-user probes.

Expected detections: AUTH-001, AUTH-002, AUTH-003, AUTH-004 and PRIV-001.

## Detection rules

| Rule | Severity | Logic |
|---|---|---|
| AUTH-001 | HIGH | 5+ failed authentication events from one source IP |
| AUTH-002 | HIGH | 5+ failed events across 3+ usernames from one source IP |
| AUTH-003 | MEDIUM | 3+ invalid-user events from one source IP |
| AUTH-004 | CRITICAL | Successful login follows earlier failed attempts from the same IP in the supplied log input |
| PRIV-001 | MEDIUM | A sudo command event is present |

Rules are intentionally simple and inspectable. Thresholds are starting points for learning, not production detection policy. Correlation uses line order; timestamps are retained as evidence.

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Application health |
| GET | /api/rules | List detection rules |
| POST | /api/analyze | Analyse supplied log text |
| GET | /api/history | List recent analyses |
| GET | /api/history/{id} | Retrieve a saved analysis |

## Data and privacy

Analyses are stored locally in data/soc_triage.db by default. Set SOC_TRIAGE_DB to override the database path. Redact personal data, tokens and internal hostnames before analysing confidential logs.

## Limitations

The parser targets a small set of common Linux SSH / sudo patterns. It is not a general-purpose SIEM and does not parse Windows Event Logs, JSON audit events or arbitrary application logs. Useful next steps include configurable thresholds, time-window correlation, event export, analyst case status, more log formats and role-based access control.
