"""Resolve discovered devices and operator rules into fetchable mesh peers."""

from dataclasses import dataclass

from discovery.mesh_config import MeshConfig, PeerRule
from discovery.tailnet import Device


@dataclass(frozen=True)
class ResolvedPeer:
    peer_id: str
    hostname: str
    dns_name: str
    ssh_target: str
    public_url: str
    source: str
    online: bool
    excluded_artifacts: tuple[str, ...]


def _resolved_discovered(device: Device, rule: PeerRule | None) -> ResolvedPeer:
    overridden = rule is not None and rule != PeerRule()
    return ResolvedPeer(
        peer_id=device.dns_name,
        hostname=device.hostname,
        dns_name=device.dns_name,
        ssh_target=rule.ssh_target if rule and rule.ssh_target else device.dns_name,
        public_url=rule.public_url if rule and rule.public_url else f"https://{device.dns_name}",
        source="overridden" if overridden else "discovered",
        online=True,
        excluded_artifacts=rule.excluded_artifacts if rule else (),
    )


def _resolved_manual(peer_id: str, rule: PeerRule) -> ResolvedPeer:
    assert rule.ssh_target is not None
    assert rule.public_url is not None
    return ResolvedPeer(
        peer_id=peer_id,
        hostname=peer_id.split(".")[0],
        dns_name=rule.ssh_target,
        ssh_target=rule.ssh_target,
        public_url=rule.public_url,
        source="manual",
        online=False,
        excluded_artifacts=rule.excluded_artifacts,
    )


def resolve_peers(devices: list[Device], config: MeshConfig) -> list[ResolvedPeer]:
    """Apply exclusions and overrides, then add configured manual peers."""
    excluded = set(config.excluded_peers)
    resolved = []
    discovered_ids = set()
    for device in devices:
        discovered_ids.add(device.dns_name)
        if device.dns_name in excluded:
            continue
        resolved.append(_resolved_discovered(device, config.peers.get(device.dns_name)))

    for peer_id, rule in config.peers.items():
        if rule.manual and peer_id not in discovered_ids and peer_id not in excluded:
            resolved.append(_resolved_manual(peer_id, rule))

    return sorted(resolved, key=lambda peer: peer.peer_id)
