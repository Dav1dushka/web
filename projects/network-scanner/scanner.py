import argparse
import concurrent.futures
import ipaddress
import socket
from typing import Iterable


def parse_ports(value: str) -> list[int]:
    ports = []

    for item in value.split(","):
        item = item.strip()

        if "-" in item:
            start, end = map(int, item.split("-", 1))
            ports.extend(range(start, end + 1))
        else:
            ports.append(int(item))

    return sorted(set(port for port in ports if 1 <= port <= 65535))


def scan_port(ip: str, port: int, timeout: float) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((ip, port)) == 0


def scan_host(ip: str, ports: Iterable[int], timeout: float) -> list[int]:
    open_ports = []

    for port in ports:
        if scan_port(ip, port, timeout):
            open_ports.append(port)

    return open_ports


def scan_network(
    network: ipaddress.IPv4Network,
    ports: list[int],
    timeout: float,
    workers: int,
) -> dict[str, list[int]]:
    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        jobs = {
            executor.submit(scan_host, str(ip), ports, timeout): str(ip)
            for ip in network.hosts()
        }

        for future in concurrent.futures.as_completed(jobs):
            ip = jobs[future]
            open_ports = future.result()

            if open_ports:
                results[ip] = open_ports

    return dict(sorted(results.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Small IPv4 TCP network scanner")
    parser.add_argument("network", help="Network in CIDR notation, e.g. 192.168.1.0/24")
    parser.add_argument(
        "--ports",
        default="22,80,443",
        help="Ports or ranges, e.g. 22,80,443,8000-8010",
    )
    parser.add_argument("--timeout", type=float, default=0.3)
    parser.add_argument("--workers", type=int, default=32)

    args = parser.parse_args()

    network = ipaddress.ip_network(args.network, strict=False)
    ports = parse_ports(args.ports)

    print(f"Scanning {network}...")
    print(f"Ports: {ports}")

    results = scan_network(
        network,
        ports,
        timeout=args.timeout,
        workers=args.workers,
    )

    if not results:
        print("No open ports found.")
        return

    for ip, open_ports in results.items():
        print(f"{ip}: {', '.join(map(str, open_ports))}")


if __name__ == "__main__":
    main()
