from pathlib import Path

from main import detect_bruteforce, ingest_line


def import_file(path: str):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    accepted = 0

    for line in lines:
        if ingest_line(line):
            accepted += 1

    alerts = detect_bruteforce()

    print(f"Accepted events: {accepted}")
    print(f"New alerts: {alerts}")


if __name__ == "__main__":
    import_logs = "sample.log"
    import_file(import_logs)
