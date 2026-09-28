from collections import Counter
from datetime import datetime
import re
import sys

FAILED_LOGIN = re.compile(
    r"^(?P<time>\S+) FAILED_LOGIN ip=(?P<ip>\S+) user=(?P<user>\S+)$"
)


def analyze(path: str, threshold: int = 5):
    failures = Counter()
    examples = {}

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            match = FAILED_LOGIN.match(line)
            if not match:
                continue

            ip = match.group("ip")
            failures[ip] += 1
            examples.setdefault(ip, match.group("time"))

    print("Failed login attempts:")

    for ip, count in failures.most_common():
        print(f"{ip}: {count}")

        if count >= threshold:
            print(f"  ALERT: possible brute-force activity ({count} attempts)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze.py sample.log")
        raise SystemExit(1)

    analyze(sys.argv[1])
