"""The discovery cycle: manifest, then peers, forever."""

import logging
import signal
import threading

from discovery.config import Config
from discovery.manifest import build_manifest
from discovery.mesh import resolve_peers
from discovery.mesh_config import load_mesh_config
from discovery.peers import build_peers
from discovery.ssh_fetch import fetch_manifest_ssh
from discovery.tailnet import Device, TailnetError, get_status
from discovery.util import write_json_atomic

log = logging.getLogger(__name__)


def _describe(device: Device | None) -> dict:
    if device is None:
        return {}
    return {
        "hostname": device.hostname,
        "dns_name": device.dns_name,
        "url": f"https://{device.dns_name}",
    }


def run_once(cfg: Config, get_status_fn=None, fetcher=fetch_manifest_ssh) -> list[dict]:
    """One cycle: rebuild manifest.json, then aggregate reachable peers into peers.json.

    A tailscaled that isn't up yet is survivable: the manifest is still written
    (with empty device info) and peers.json becomes an empty list.
    """
    if get_status_fn is None:
        get_status_fn = lambda socket_path: get_status(socket_path)  # noqa: E731

    self_device, peer_devices = None, []
    try:
        self_device, peer_devices = get_status_fn(cfg.socket_path)
    except TailnetError as exc:
        log.warning("tailnet status unavailable: %s", exc)

    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(cfg.artifacts_dir, device=_describe(self_device))
    write_json_atomic(cfg.output_dir / "manifest.json", manifest)

    mesh_config = load_mesh_config(cfg.mesh_config_path).config
    resolved_peers = resolve_peers(peer_devices, mesh_config)
    peers_doc = build_peers(
        resolved_peers,
        fetcher=fetcher,
        timeout=cfg.fetch_timeout,
        socket_path=cfg.socket_path,
    )
    write_json_atomic(cfg.output_dir / "peers.json", peers_doc)

    log.info(
        "cycle complete: %d artifact(s), %d/%d peer(s) responded",
        len(manifest["artifacts"]),
        len(peers_doc["peers"]),
        len(peer_devices),
    )
    return [
        {"hostname": peer.hostname, "dns_name": peer.dns_name, "online": True}
        for peer in peer_devices
    ]


def run_forever(cfg: Config) -> None:
    stop = threading.Event()

    def handle_signal(signum, frame):
        log.info("received signal %d, shutting down", signum)
        stop.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    log.info(
        "discovery starting: artifacts=%s output=%s interval=%.0fs timeout=%.1fs socket=%s",
        cfg.artifacts_dir,
        cfg.output_dir,
        cfg.interval,
        cfg.fetch_timeout,
        cfg.socket_path,
    )
    while not stop.is_set():
        try:
            run_once(cfg)
        except Exception:
            log.exception("discovery cycle failed; will retry next interval")
        stop.wait(cfg.interval)
