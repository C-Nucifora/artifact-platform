"""Tests for fetching a peer's /manifest.json over HTTPS."""

import json
import time

from discovery.fetch import MAX_BODY_BYTES, fetch_manifest
from discovery.tailnet import Device

PEER = Device(hostname="pi", dns_name="pi.tail1234.ts.net", ips=("100.64.0.2",))
GOOD_MANIFEST = {"version": 1, "device": {}, "artifacts": [{"slug": "clock"}]}


class FakeResponse:
    def __init__(self, status=200, body=b""):
        self.status = status
        self._body = body

    def read(self, amt=None):
        if amt is None:
            return self._body
        chunk, self._body = self._body[:amt], self._body[amt:]
        return chunk


class FakeConnection:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.requests = []
        self.closed = False
        self.host = None
        self.server_hostname = None

    def factory(self):
        def make(host, server_hostname, timeout):
            self.host = host
            self.server_hostname = server_hostname
            self.timeout = timeout
            return self

        return make

    def request(self, method, url, headers=None):
        if self._error is not None:
            raise self._error
        self.requests.append((method, url, headers or {}))

    def getresponse(self):
        return self._response

    def close(self):
        self.closed = True


def test_valid_manifest_returned():
    conn = FakeConnection(FakeResponse(200, json.dumps(GOOD_MANIFEST).encode()))
    result = fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory())
    assert result == GOOD_MANIFEST
    assert conn.closed


def test_connects_to_ip_with_dns_name_as_sni():
    conn = FakeConnection(FakeResponse(200, json.dumps(GOOD_MANIFEST).encode()))
    fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory())
    assert conn.host == "100.64.0.2"
    assert conn.server_hostname == "pi.tail1234.ts.net"
    (method, url, headers) = conn.requests[0]
    assert (method, url) == ("GET", "/manifest.json")
    assert headers["Host"] == "pi.tail1234.ts.net"


def test_falls_back_to_dns_name_when_no_ips():
    peer = Device(hostname="pi", dns_name="pi.tail1234.ts.net", ips=())
    conn = FakeConnection(FakeResponse(200, json.dumps(GOOD_MANIFEST).encode()))
    fetch_manifest(peer, timeout=2.0, connection_factory=conn.factory())
    assert conn.host == "pi.tail1234.ts.net"


def test_http_error_status_returns_none():
    conn = FakeConnection(FakeResponse(404, b"not found"))
    assert fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory()) is None
    assert conn.closed


def test_garbage_body_returns_none():
    conn = FakeConnection(FakeResponse(200, b"<html>surprise!</html>"))
    assert fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory()) is None


def test_non_object_json_returns_none():
    conn = FakeConnection(FakeResponse(200, b'["json", "but", "wrong"]'))
    assert fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory()) is None


def test_object_without_artifacts_list_returns_none():
    conn = FakeConnection(FakeResponse(200, b'{"hello": "world"}'))
    assert fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory()) is None


def test_artifacts_not_a_list_returns_none():
    conn = FakeConnection(FakeResponse(200, b'{"artifacts": "nope"}'))
    assert fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory()) is None


def test_oversized_body_returns_none():
    huge = b'{"artifacts": ["' + b"x" * MAX_BODY_BYTES + b'"]}'
    conn = FakeConnection(FakeResponse(200, huge))
    assert fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory()) is None


def test_nan_constant_rejected():
    # json.loads accepts NaN by default; re-emitting it would produce a
    # peers.json that browsers refuse to parse.
    conn = FakeConnection(FakeResponse(200, b'{"artifacts": [{"title": NaN}]}'))
    assert fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory()) is None


def test_infinity_constant_rejected():
    conn = FakeConnection(FakeResponse(200, b'{"artifacts": [{"title": Infinity}]}'))
    assert fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory()) is None


def test_trickling_body_gives_up_at_deadline():
    class TricklingResponse:
        status = 200

        def read(self, amt=None):
            time.sleep(0.05)
            return b"x"  # never terminates, never exceeds the size cap quickly

    conn = FakeConnection(TricklingResponse())
    start = time.monotonic()
    assert fetch_manifest(PEER, timeout=0.2, connection_factory=conn.factory()) is None
    assert time.monotonic() - start < 5.0
    assert conn.closed


def test_connection_error_returns_none():
    conn = FakeConnection(error=OSError("connection refused"))
    assert fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory()) is None
    assert conn.closed


def test_timeout_error_returns_none():
    conn = FakeConnection(error=TimeoutError("timed out"))
    assert fetch_manifest(PEER, timeout=2.0, connection_factory=conn.factory()) is None
