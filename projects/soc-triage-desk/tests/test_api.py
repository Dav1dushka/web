def test_dashboard_rules_analyze_and_history(tmp_path, monkeypatch):
    monkeypatch.setenv("SOC_TRIAGE_DB", str(tmp_path / "soc-test.db"))
    from app.main import app
    from fastapi.testclient import TestClient

    sample = (
        "2026-11-22T08:10:00Z srv sshd: Failed password for admin from 203.0.113.45 port 20 ssh2\n"
        "2026-11-22T08:10:01Z srv sshd: Failed password for root from 203.0.113.45 port 21 ssh2\n"
        "2026-11-22T08:10:02Z srv sshd: Failed password for test from 203.0.113.45 port 22 ssh2\n"
        "2026-11-22T08:10:03Z srv sshd: Failed password for alice from 203.0.113.45 port 23 ssh2\n"
        "2026-11-22T08:10:04Z srv sshd: Failed password for deploy from 203.0.113.45 port 24 ssh2"
    )
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/static/style.css").status_code == 200
        assert client.get("/health").json()["status"] == "ok"
        assert len(client.get("/api/rules").json()) == 5
        response = client.post("/api/analyze", json={"source_name":"unit test log","log_text":sample})
        assert response.status_code == 201
        analysis_id = response.json()["id"]
        assert response.json()["summary"]["parsed_events"] == 5
        assert response.json()["summary"]["incidents"] >= 2
        history = client.get("/api/history")
        assert history.status_code == 200
        assert history.json()[0]["source_name"] == "unit test log"
        detail = client.get("/api/history/" + str(analysis_id))
        assert detail.status_code == 200
        assert detail.json()["result"]["summary"]["parsed_events"] == 5
