import time
import urllib.request

URLS = [
    "https://example.com",
]


def check(url: str) -> tuple[bool, int | None]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return True, response.status
    except Exception:
        return False, None


def run():
    while True:
        for url in URLS:
            ok, status = check(url)

            if ok:
                print(f"[UP]   {url} -> {status}")
            else:
                print(f"[DOWN] {url}")

        time.sleep(30)


if __name__ == "__main__":
    run()
