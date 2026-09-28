# Network Scanner

A small Python project I made to practice networking.

It scans an IPv4 network and checks selected TCP ports.

### Example

```bash
python scanner.py 192.168.1.0/24 --ports 22,80,443
```

Example output:

```
192.168.1.1: 80, 443
192.168.1.10: 22
```

### Built with

Python, sockets, threading and ipaddress.

I'm using this to learn more about TCP, ports, IP addresses and concurrent network operations.

Only scan networks and devices you are allowed to test.
