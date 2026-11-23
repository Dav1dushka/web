from __future__ import annotations

import ipaddress
import re
from collections import defaultdict

IPV4 = r"(?:\d{1,3}\.){3}\d{1,3}"
PREFIX = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)\s+"
    r"(?P<host>\S+)\s+(?P<process>[\w.-]+)(?:\[\d+\])?:\s*(?P<message>.*)$"
)
FAILED = re.compile(
    rf"Failed password for (?:(?P<invalid>invalid user)\s+)?(?P<username>\S+) from (?P<ip>{IPV4})",
    re.IGNORECASE,
)
ACCEPTED = re.compile(
    rf"Accepted (?:password|publickey) for (?P<username>\S+) from (?P<ip>{IPV4})",
    re.IGNORECASE,
)
INVALID_USER = re.compile(
    rf"Invalid user (?P<username>\S+) from (?P<ip>{IPV4})",
    re.IGNORECASE,
)
SUDO = re.compile(
    r"sudo:\s*(?P<username>[a-zA-Z0-9_.-]+)\s*:.*?COMMAND=(?P<command>.+)$",
    re.IGNORECASE,
)


def _valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def parse_line(line: str, line_number: int) -> dict | None:
    raw = line.strip()
    if not raw:
        return None

    match = PREFIX.match(raw)
    if match:
        timestamp = match.group("timestamp")
        host = match.group("host")
        process = match.group("process")
        message = match.group("message")
    else:
        timestamp, host, process, message = None, None, None, raw

    for event_type, pattern in (
        ("failed_login", FAILED),
        ("invalid_user", INVALID_USER),
        ("successful_login", ACCEPTED),
    ):
        found = pattern.search(message)
        if found:
            source_ip = found.group("ip")
            if not _valid_ip(source_ip):
                return None
            return {
                "line_number": line_number,
                "timestamp": timestamp,
                "host": host,
                "process": process,
                "event_type": event_type,
                "username": found.group("username"),
                "source_ip": source_ip,
                "command": None,
                "raw": raw,
            }

    # The parsed syslog prefix removes "sudo:" from the message.
    sudo_pattern = re.compile(
        r"^(?P<username>[a-zA-Z0-9_.-]+)\s*:.*?COMMAND=(?P<command>.+)$",
        re.IGNORECASE,
    )
    sudo = sudo_pattern.search(message) if (process or "").lower() == "sudo" else SUDO.search(message)
    if sudo:
        return {
            "line_number": line_number,
            "timestamp": timestamp,
            "host": host,
            "process": process or "sudo",
            "event_type": "privileged_command",
            "username": sudo.group("username"),
            "source_ip": None,
            "command": sudo.group("command").strip(),
            "raw": raw,
        }
    return None


def parse_log(log_text: str) -> tuple[list[dict], int]:
    events = []
    ignored = 0
    for line_number, line in enumerate(log_text.splitlines(), start=1):
        event = parse_line(line, line_number)
        if event is None:
            if line.strip():
                ignored += 1
        else:
            events.append(event)
    return events, ignored


def _incident(rule_id: str, title: str, severity: str, description: str, events: list[dict]) -> dict:
    ips = sorted({event["source_ip"] for event in events if event.get("source_ip")})
    users = sorted({event["username"] for event in events if event.get("username")})
    timestamps = [event["timestamp"] for event in events if event.get("timestamp")]
    return {
        "rule_id": rule_id,
        "title": title,
        "severity": severity,
        "description": description,
        "event_count": len(events),
        "source_ips": ips,
        "usernames": users,
        "first_seen": min(timestamps) if timestamps else None,
        "last_seen": max(timestamps) if timestamps else None,
        "evidence": [
            {
                "line_number": event["line_number"],
                "timestamp": event["timestamp"],
                "event_type": event["event_type"],
                "username": event["username"],
                "source_ip": event["source_ip"],
                "raw": event["raw"],
            }
            for event in events[:5]
        ],
    }


def detect_incidents(events: list[dict]) -> list[dict]:
    """Apply explainable defensive heuristics to parsed events."""
    by_ip: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("source_ip"):
            by_ip[event["source_ip"]].append(event)

    incidents = []
    for source_ip, ip_events in by_ip.items():
        failures = [e for e in ip_events if e["event_type"] in {"failed_login", "invalid_user"}]
        successes = [e for e in ip_events if e["event_type"] == "successful_login"]
        invalids = [e for e in ip_events if e["event_type"] == "invalid_user"]
        usernames = {e["username"] for e in failures if e.get("username")}

        if len(failures) >= 5:
            incidents.append(_incident(
                "AUTH-001", "Repeated failed authentication", "HIGH",
                f"{len(failures)} failed authentication events were recorded from {source_ip}. Review whether this activity is expected.",
                failures,
            ))
        if len(failures) >= 5 and len(usernames) >= 3:
            incidents.append(_incident(
                "AUTH-002", "Possible password spraying", "HIGH",
                f"The source attempted authentication against {len(usernames)} usernames. Validate against normal user activity.",
                failures,
            ))
        if len(invalids) >= 3:
            incidents.append(_incident(
                "AUTH-003", "Repeated invalid-user probes", "MEDIUM",
                f"{len(invalids)} attempts referenced invalid usernames from {source_ip}. Review the targeted account names.",
                invalids,
            ))
        if failures and successes:
            first_success_line = min(e["line_number"] for e in successes)
            prior_failures = [e for e in failures if e["line_number"] < first_success_line]
            if prior_failures:
                correlated = prior_failures + [e for e in successes if e["line_number"] == first_success_line]
                incidents.append(_incident(
                    "AUTH-004", "Successful login after failed attempts", "CRITICAL",
                    "A successful authentication from the same source followed earlier failures in this log input. Confirm the login is legitimate.",
                    correlated,
                ))

    for event in events:
        if event["event_type"] == "privileged_command":
            incidents.append(_incident(
                "PRIV-001", "Privileged command executed", "MEDIUM",
                f"User {event['username']} executed a command through sudo. Validate the command and change context.",
                [event],
            ))

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    incidents.sort(key=lambda item: (severity_order[item["severity"]], item["rule_id"], item["source_ips"]))
    return incidents


def analyze_log(log_text: str) -> dict:
    if len(log_text) > 1_000_000:
        raise ValueError("Log input exceeds the 1 MB limit.")
    events, ignored = parse_log(log_text)
    incidents = detect_incidents(events)
    return {
        "summary": {
            "total_lines": len(log_text.splitlines()),
            "parsed_events": len(events),
            "ignored_lines": ignored,
            "incidents": len(incidents),
            "critical": sum(i["severity"] == "CRITICAL" for i in incidents),
            "high": sum(i["severity"] == "HIGH" for i in incidents),
            "medium": sum(i["severity"] == "MEDIUM" for i in incidents),
        },
        "events": events,
        "incidents": incidents,
    }
