import ipaddress

from scanner import parse_ports, scan_network


def test_parse_ports():
    assert parse_ports("22,80,443,8000-8002") == [22, 80, 443, 8000, 8001, 8002]


def test_parse_network():
    network = ipaddress.ip_network("192.168.1.0/30")
    assert str(network.network_address) == "192.168.1.0"
    assert str(network.broadcast_address) == "192.168.1.3"
