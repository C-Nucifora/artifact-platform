from discovery.mesh import resolve_peers
from discovery.mesh_config import parse_mesh_config
from discovery.tailnet import Device


def device(name):
    return Device(
        hostname=name,
        dns_name=f"{name}.tail1234.ts.net",
        ips=("100.64.0.2",),
    )


def config(raw=None):
    return parse_mesh_config(raw or {"version": 1}).config


def test_every_discovered_device_meshes_by_default():
    peers = resolve_peers([device("pi"), device("studio")], config())

    assert [peer.peer_id for peer in peers] == [
        "pi.tail1234.ts.net",
        "studio.tail1234.ts.net",
    ]
    assert peers[0].ssh_target == "pi.tail1234.ts.net"
    assert peers[0].public_url == "https://pi.tail1234.ts.net"
    assert peers[0].source == "discovered"
    assert peers[0].online is True


def test_excluded_peer_is_removed_before_fetch_resolution():
    mesh = config({"version": 1, "excluded_peers": ["pi.tail1234.ts.net"]})

    assert resolve_peers([device("pi"), device("studio")], mesh)[0].hostname == "studio"


def test_discovered_peer_accepts_endpoint_and_artifact_overrides():
    mesh = config(
        {
            "version": 1,
            "peers": {
                "pi.tail1234.ts.net": {
                    "ssh_target": "pi-reader.tail1234.ts.net",
                    "public_url": "https://artifacts.example.com/pi",
                    "excluded_artifacts": ["private-demo"],
                }
            },
        }
    )

    resolved = resolve_peers([device("pi")], mesh)[0]

    assert resolved.ssh_target == "pi-reader.tail1234.ts.net"
    assert resolved.public_url == "https://artifacts.example.com/pi"
    assert resolved.excluded_artifacts == ("private-demo",)
    assert resolved.source == "overridden"


def test_manual_peer_is_included_when_not_discovered():
    mesh = config(
        {
            "version": 1,
            "peers": {
                "workshop": {
                    "manual": True,
                    "ssh_target": "workshop.tail1234.ts.net",
                    "public_url": "https://workshop.example.com",
                }
            },
        }
    )

    resolved = resolve_peers([], mesh)[0]

    assert resolved.peer_id == "workshop"
    assert resolved.hostname == "workshop"
    assert resolved.dns_name == "workshop.tail1234.ts.net"
    assert resolved.source == "manual"
    assert resolved.online is False


def test_non_manual_override_does_not_create_an_absent_peer():
    mesh = config(
        {
            "version": 1,
            "peers": {"pi.tail1234.ts.net": {"public_url": "https://pi.example.com"}},
        }
    )

    assert resolve_peers([], mesh) == []


def test_discovered_manual_record_is_not_duplicated():
    mesh = config(
        {
            "version": 1,
            "peers": {
                "pi.tail1234.ts.net": {
                    "manual": True,
                    "ssh_target": "pi.tail1234.ts.net",
                    "public_url": "https://pi.example.com",
                }
            },
        }
    )

    peers = resolve_peers([device("pi")], mesh)

    assert len(peers) == 1
    assert peers[0].online is True
    assert peers[0].source == "overridden"
