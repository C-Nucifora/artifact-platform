"""Fetch a peer's /manifest.json over HTTPS.

Connects to the peer's Tailscale IP with TLS SNI (and certificate validation)
against its MagicDNS name, so nothing here depends on in-container DNS.
"""

import http.client
import json
import logging
import socket
import ssl
import time

from discovery.tailnet import Device

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 1_000_000
CHUNK_BYTES = 65_536
# Socket timeouts reset on every recv, so a peer trickling bytes could hold a
# thread open indefinitely. Cap the whole exchange at this multiple instead.
TOTAL_BUDGET_FACTOR = 3
USER_AGENT = "artifact-platform-discovery/1"


def _reject_constant(name):
    # json.loads accepts NaN/Infinity by default; re-emitting those produces a
    # peers.json that no browser's JSON.parse will accept.
    raise ValueError(f"non-standard JSON constant: {name}")


class SNIHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection that connects to `host` (an IP) but does TLS for `server_hostname`."""

    def __init__(self, host: str, server_hostname: str, timeout: float):
        super().__init__(host, 443, timeout=timeout, context=ssl.create_default_context())
        self._server_hostname = server_hostname

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self._server_hostname)


def _read_body(response, deadline_at: float) -> bytes:
    """Read up to MAX_BODY_BYTES + 1 bytes, giving up if the deadline passes."""
    chunks: list[bytes] = []
    total = 0
    while total <= MAX_BODY_BYTES:
        if time.monotonic() > deadline_at:
            raise TimeoutError("body read exceeded deadline")
        chunk = response.read(min(CHUNK_BYTES, MAX_BODY_BYTES + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


def fetch_manifest(
    device: Device,
    timeout: float = 5.0,
    connection_factory=SNIHTTPSConnection,
) -> dict | None:
    """Return the peer's manifest, or None if it can't be fetched or isn't one.

    Any transport error, non-200 status, oversized body, or body that isn't a
    JSON object with an "artifacts" list means None — peers that aren't running
    the platform are expected, not exceptional.
    """
    host = device.ips[0] if device.ips else device.dns_name
    deadline_at = time.monotonic() + timeout * TOTAL_BUDGET_FACTOR
    conn = None
    try:
        conn = connection_factory(host=host, server_hostname=device.dns_name, timeout=timeout)
        conn.request(
            "GET",
            "/manifest.json",
            headers={
                "Host": device.dns_name,
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        response = conn.getresponse()
        if response.status != 200:
            log.debug("%s: /manifest.json returned %s", device.dns_name, response.status)
            return None
        body = _read_body(response, deadline_at)
        if len(body) > MAX_BODY_BYTES:
            log.debug("%s: manifest larger than %d bytes", device.dns_name, MAX_BODY_BYTES)
            return None
        manifest = json.loads(body, parse_constant=_reject_constant)
    except (
        OSError,
        ssl.SSLError,
        http.client.HTTPException,
        ValueError,  # covers JSONDecodeError and rejected NaN/Infinity constants
        UnicodeDecodeError,
    ) as exc:
        log.debug("%s: fetch failed: %s", device.dns_name, exc)
        return None
    finally:
        if conn is not None:
            conn.close()

    if not isinstance(manifest, dict) or not isinstance(manifest.get("artifacts"), list):
        log.debug("%s: response is JSON but not a manifest", device.dns_name)
        return None
    return manifest
