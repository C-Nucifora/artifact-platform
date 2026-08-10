"""Retrieve peer manifests through identity-authenticated Tailscale SSH."""

import json
import logging
import subprocess

from discovery.mesh import ResolvedPeer

log = logging.getLogger(__name__)

MAX_MANIFEST_BYTES = 1024 * 1024


def _run_ssh(argv: list[str], timeout: float) -> str:
    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return result.stdout


def fetch_manifest_ssh(
    peer: ResolvedPeer,
    socket_path: str,
    timeout: float,
    runner=_run_ssh,
) -> dict | None:
    """Return a peer manifest, or None when the bounded SSH read fails."""
    argv = [
        "tailscale",
        "--socket",
        socket_path,
        "ssh",
        f"artifact@{peer.ssh_target}",
        "cat",
        "/generated/manifest.json",
    ]
    try:
        raw = runner(argv, timeout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        log.debug("%s: Tailscale SSH failed: %s", peer.peer_id, exc)
        return None
    if len(raw.encode("utf-8")) > MAX_MANIFEST_BYTES:
        log.debug("%s: manifest exceeded size limit", peer.peer_id)
        return None
    try:
        manifest = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError):
        log.debug("%s: manifest was not valid JSON", peer.peer_id)
        return None
    if not isinstance(manifest, dict) or not isinstance(manifest.get("artifacts"), list):
        log.debug("%s: manifest shape was invalid", peer.peer_id)
        return None
    return manifest
