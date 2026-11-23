from app.core import analyze_log, parse_line

SAMPLE = """2026-11-22T08:10:00Z srv-auth-01 sshd[2101]: Failed password for invalid user admin from 203.0.113.45 port 50110 ssh2
2026-11-22T08:10:08Z srv-auth-01 sshd[2102]: Failed password for invalid user administrator from 203.0.113.45 port 50111 ssh2
2026-11-22T08:10:15Z srv-auth-01 sshd[2103]: Failed password for test from 203.0.113.45 port 50112 ssh2
2026-11-22T08:10:22Z srv-auth-01 sshd[2104]: Failed password for deploy from 203.0.113.45 port 50113 ssh2
2026-11-22T08:10:29Z srv-auth-01 sshd[2105]: Failed password for alice from 203.0.113.45 port 50114 ssh2
2026-11-22T08:11:02Z srv-auth-01 sshd[2106]: Accepted publickey for alice from 203.0.113.45 port 50115 ssh2
2026-11-22T08:15:10Z srv-auth-01 sudo: alice : TTY=pts/0 ; PWD=/home/alice ; USER=root ; COMMAND=/usr/bin/systemctl restart nginx
"""


def test_parse_failed_login():
    event = parse_line("2026-11-22T08:10:00Z srv sshd[10]: Failed password for admin from 203.0.113.7 port 20 ssh2", 1)
    assert event["event_type"] == "failed_login"
    assert event["username"] == "admin"
    assert event["source_ip"] == "203.0.113.7"


def test_parse_successful_login():
    event = parse_line("2026-11-22T08:10:00Z srv sshd[10]: Accepted publickey for alice from 198.51.100.2 port 20 ssh2", 1)
    assert event["event_type"] == "successful_login"


def test_parse_sudo_command():
    event = parse_line("2026-11-22T08:10:00Z srv sudo: alice : TTY=pts/0 ; COMMAND=/usr/bin/id", 1)
    assert event["event_type"] == "privileged_command"
    assert event["command"] == "/usr/bin/id"


def test_ignores_unrecognized_and_invalid_ips():
    assert parse_line("ordinary application message", 1) is None
    assert parse_line("2026-11-22T08:10:00Z srv sshd: Failed password for admin from 999.999.1.2 port 10 ssh2", 2) is None


def test_detects_password_spraying_and_success_after_failures():
    result = analyze_log(SAMPLE)
    rule_ids = {item["rule_id"] for item in result["incidents"]}
    assert "AUTH-001" in rule_ids
    assert "AUTH-002" in rule_ids
    assert "AUTH-004" in rule_ids
    assert "PRIV-001" in rule_ids


def test_detects_invalid_user_probes():
    sample = "\n".join(
        f"2026-11-22T08:10:0{i}Z srv sshd: Invalid user test{i} from 203.0.113.8 port 22 ssh2"
        for i in range(3)
    )
    result = analyze_log(sample)
    assert "AUTH-003" in {item["rule_id"] for item in result["incidents"]}


def test_summary_counts_lines_and_events():
    result = analyze_log(SAMPLE)
    assert result["summary"]["total_lines"] == 7
    assert result["summary"]["parsed_events"] == 7
    assert result["summary"]["incidents"] >= 4


def test_rejects_oversized_log():
    try:
        analyze_log("x" * 1_000_001)
    except ValueError as exc:
        assert "1 MB" in str(exc)
    else:
        raise AssertionError("Expected input size guard to reject oversized content")
