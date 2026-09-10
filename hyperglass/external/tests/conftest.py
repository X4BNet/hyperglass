"""Keep external-client unit tests independent of public service availability."""

# Standard Library
import json
from functools import partial

# Third Party
import httpx
import pytest

# Project
from hyperglass.state import use_state
from hyperglass.external._base import BaseExternal


@pytest.fixture(autouse=True)
def external_http(monkeypatch):
    """Exercise real request construction and parsing with HTTP transport fixtures."""

    def respond(request):
        if request.url.host == "httpbin.org":
            if request.url.path == "/delay/4":
                raise httpx.ReadTimeout("Simulated slow response", request=request)
            return httpx.Response(
                200,
                json={
                    "url": str(request.url),
                    "args": dict(request.url.params),
                    "json": json.loads(request.content) if request.content else None,
                },
            )
        if request.url.host == "rpki.cloudflare.com":
            payload = json.loads(request.content)
            assert request.url.path == "/api/graphql"
            states = {
                'validation(prefix: "103.21.244.0/24", asn: 13335)': "Invalid",
                'validation(prefix: "1.1.1.0/24", asn: 13335)': "Valid",
                'validation(prefix: "192.0.2.0/24", asn: 65000)': "NotFound",
            }
            for query, state in states.items():
                if query in payload["query"]:
                    return httpx.Response(200, json={"data": {"validation": {"state": state}}})
        raise AssertionError(f"Unexpected external request: {request.method} {request.url}")

    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(httpx, "Client", partial(httpx.Client, transport=transport))
    monkeypatch.setattr(httpx, "AsyncClient", partial(httpx.AsyncClient, transport=transport))
    monkeypatch.setattr(BaseExternal, "_test", lambda self: True)
    use_state("cache").delete("hyperglass.external.rpki")
