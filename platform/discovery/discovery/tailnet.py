"""Query the local tailscaled for this device and its online peers."""

import json
import subprocess
from dataclasses import dataclass

STATUS_TIMEOUT = 10.0


class TailnetError(Exception):
    """tailscale status could not be run or produced unusable output."""


@dataclass(frozen=True)
class Device:
    hostname: str
    dns_name: str  # fully qualified, no trailing dot
    ips: tuple[str, ...]


def _run_tailscale_status(socket_path: str, timeout: float) -> str:
    result = subprocess.run(
        ["tailscale", "--socket", socket_path, "status", "--json"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return result.stdout


def _device_from(node: dict) -> Device | None:
    dns_name = node.get("DNSName") or ""
    dns_name = dns_name.rstrip(".")
    if not dns_name:
        return None
    ips = node.get("TailscaleIPs") or []
    return Device(
        hostname=node.get("HostName") or dns_name.split(".")[0],
        dns_name=dns_name,
        ips=tuple(ip for ip in ips if isinstance(ip, str)),
    )


def get_status(
    socket_path: str, runner=_run_tailscale_status
) -> tuple[Device | None, list[Device]]:
    """Return (self_device, online_peers) from `tailscale status --json`.

    Raises TailnetError when the CLI is missing, fails, times out, or returns
    output that isn't a JSON status object.
    """
    try:
        raw = runner(socket_path, STATUS_TIMEOUT)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise TailnetError(f"tailscale status failed: {exc}") from exc

    try:
        status = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TailnetError(f"tailscale status returned invalid JSON: {exc}") from exc
    if not isinstance(status, dict):
        raise TailnetError("tailscale status JSON is not an object")

    self_device = _device_from(status.get("Self") or {})

    peers = []
    for node in (status.get("Peer") or {}).values():
        if not isinstance(node, dict) or not node.get("Online"):
            continue
        device = _device_from(node)
        if device is not None:
            peers.append(device)
    peers.sort(key=lambda d: d.dns_name)
    return self_device, peers
