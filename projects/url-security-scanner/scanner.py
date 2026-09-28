import argparse
import socket
import ssl
from urllib.parse import urlparse

import requests


SECURITY_HEADERS = {
    "strict-transport-security": "HSTS",
    "content-security-policy": "CSP",
    "x-frame-options": "X-Frame-Options",
    "x-content-type-options": "X-Content-Type-Options",
    "referrer-policy": "Referrer-Policy",
}


def get_tls_info(host: str, port: int = 443) -> tuple[bool, str | None]:
    context = ssl.create_default_context()

    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls:
                return True, tls.version()
    except (OSError, ssl.SSLError):
        return False, None


def scan(url: str):
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Enter a full URL such as https://example.com")

    response = requests.get(
        url,
        timeout=10,
        allow_redirects=True,
        headers={"User-Agent": "Davyd-URL-Security-Scanner/1.0"},
    )

    final_url = response.url
    headers = {key.lower(): value for key, value in response.headers.items()}

    print(f"URL: {final_url}")
    print(f"Status: {response.status_code}")
    print(f"Server: {response.headers.get('Server', 'not provided')}")
    print()

    if parsed.hostname:
        if final_url.startswith("https://"):
            tls_ok, tls_version = get_tls_info(parsed.hostname)
            print(f"TLS: {'OK' if tls_ok else 'FAILED'}")
            if tls_version:
                print(f"TLS version: {tls_version}")
        else:
            print("TLS: not used")

    print()
    print("Security headers:")

    for header, name in SECURITY_HEADERS.items():
        if header in headers:
            print(f"[OK]   {name}")
        else:
            print(f"[MISS] {name}")

    print()
    print("Redirects:")
    for item in response.history:
        print(f"  {item.status_code} -> {item.headers.get('Location', '')}")
    print(f"  {response.status_code} -> {response.url}")


def main():
    parser = argparse.ArgumentParser(
        description="Small defensive HTTP security header checker"
    )
    parser.add_argument("url", help="URL to inspect, e.g. https://example.com")
    args = parser.parse_args()

    try:
        scan(args.url)
    except requests.RequestException as exc:
        print(f"Request failed: {exc}")
    except ValueError as exc:
        print(f"Input error: {exc}")


if __name__ == "__main__":
    main()
