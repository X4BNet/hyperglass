"""Test bgp.tools interactions."""

# Standard Library
import asyncio
from unittest.mock import AsyncMock, Mock

# Third Party
import pytest

# Project
from hyperglass.state import use_state

# Local
from ..bgptools import run_whois, parse_whois, network_info

WHOIS_OUTPUT = """AS    | IP      | BGP Prefix | CC | Registry | Allocated  | AS Name
13335 | 1.1.1.1 | 1.1.1.0/24 | US | ARIN     | 2010-07-14 | Cloudflare, Inc."""


@pytest.fixture(autouse=True)
def whois_connection(monkeypatch):
    """Exercise WHOIS framing and parsing without opening an internet socket."""
    writer = Mock()
    writer.drain = AsyncMock()
    writer.can_write_eof.return_value = True

    async def connect(host, port):
        assert (host, port) == ("bgp.tools", 43)
        reader = asyncio.StreamReader()
        reader.feed_data(WHOIS_OUTPUT.encode())
        reader.feed_eof()
        return reader, writer

    monkeypatch.setattr(asyncio, "open_connection", connect)
    use_state("cache").delete("hyperglass.external.bgptools")
    return writer


# Ignore asyncio deprecation warning about loop
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_network_info():
    checks = (
        ("192.0.2.1", {"asn": "None", "rir": "Private Address"}),
        ("127.0.0.1", {"asn": "None", "rir": "Loopback Address"}),
        ("fe80:dead:beef::1", {"asn": "None", "rir": "Link Local Address"}),
        ("2001:db8::1", {"asn": "None", "rir": "Private Address"}),
        ("1.1.1.1", {"asn": "13335", "rir": "ARIN"}),
    )
    for addr, fields in checks:
        info = asyncio.run(network_info(addr))
        assert addr in info
        for key, expected in fields.items():
            assert info[addr][key] == expected


# Ignore asyncio deprecation warning about loop
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_whois(whois_connection):
    addr = "192.0.2.1"
    response = asyncio.run(run_whois([addr]))
    assert isinstance(response, str)
    assert response == WHOIS_OUTPUT
    whois_connection.write.assert_called_once_with(b"begin\n192.0.2.1\nend\n")
    whois_connection.close.assert_called_once()


def test_whois_parser():
    addr = "1.1.1.1"
    result = parse_whois(WHOIS_OUTPUT, [addr])
    assert isinstance(result, dict)
    assert addr in result, "Address missing"
    assert result[addr]["asn"] == "13335"
    assert result[addr]["rir"] == "ARIN"
    assert result[addr]["org"] == "Cloudflare, Inc."
