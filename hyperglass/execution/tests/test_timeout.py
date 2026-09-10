"""Verify SSH work and query timeouts do not block or alarm unrelated requests."""

# Standard Library
import time
import asyncio
from types import SimpleNamespace

# Third Party
import pytest

# Project
from hyperglass.execution import main
from hyperglass.execution.drivers.ssh_netmiko import NetmikoConnection


def test_ssh_collection_keeps_event_loop_responsive(monkeypatch):
    connection = object.__new__(NetmikoConnection)

    def slow_collect(*args):
        time.sleep(0.1)
        return ("SSH output",)

    monkeypatch.setattr(connection, "_collect", slow_collect)

    async def run():
        task = asyncio.create_task(connection.collect())
        await asyncio.sleep(0.01)
        assert not task.done()
        assert await task == ("SSH output",)

    asyncio.run(run())


def test_query_timeout_is_scoped_to_request(monkeypatch):
    params = SimpleNamespace(request_timeout=1.01, messages=SimpleNamespace(general="error"))
    monkeypatch.setattr(main, "use_state", lambda _: params)
    monkeypatch.setattr(main, "DeviceTimeout", lambda **kwargs: TimeoutError("SSH timed out"))

    class Driver:
        def __init__(self, *args):
            pass

        async def collect(self):
            await asyncio.sleep(10)

    monkeypatch.setattr(main, "map_driver", lambda _: Driver)
    query = SimpleNamespace(
        device=SimpleNamespace(id="test", driver="netmiko", proxy=None), summary=lambda: "test"
    )
    with pytest.raises(TimeoutError, match="SSH timed out"):
        asyncio.run(main.execute(query))
