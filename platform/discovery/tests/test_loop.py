"""Tests for a single discovery cycle and env-based configuration."""

import json

import pytest

from discovery.config import Config
from discovery.loop import run_once
from discovery.tailnet import Device, TailnetError

SELF = Device(hostname="studio", dns_name="studio.tail1234.ts.net", ips=("100.64.0.1",))
PEER = Device(hostname="pi", dns_name="pi.tail1234.ts.net", ips=("100.64.0.2",))
PEER_MANIFEST = {"version": 1, "device": {"hostname": "pi"}, "artifacts": []}


@pytest.fixture
def cfg(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "demo").mkdir()
    (artifacts / "demo" / "index.html").write_text("<h1>demo</h1>")
    return Config(
        artifacts_dir=artifacts,
        output_dir=tmp_path / "out",
        interval=120.0,
        fetch_timeout=1.0,
        socket_path="/tmp/sock",
    )


def read_json(path):
    return json.loads(path.read_text())


def test_run_once_writes_manifest_and_peers(cfg):
    run_once(
        cfg,
        get_status_fn=lambda socket_path: (SELF, [PEER]),
        fetcher=lambda device, timeout: PEER_MANIFEST,
    )

    manifest = read_json(cfg.output_dir / "manifest.json")
    assert manifest["device"]["dns_name"] == "studio.tail1234.ts.net"
    assert manifest["device"]["url"] == "https://studio.tail1234.ts.net"
    assert [a["slug"] for a in manifest["artifacts"]] == ["demo"]

    peers = read_json(cfg.output_dir / "peers.json")
    assert [p["dns_name"] for p in peers["peers"]] == ["pi.tail1234.ts.net"]


def test_run_once_survives_tailnet_error(cfg):
    def failing_status(socket_path):
        raise TailnetError("tailscaled not up yet")

    run_once(cfg, get_status_fn=failing_status, fetcher=lambda device, timeout: None)

    manifest = read_json(cfg.output_dir / "manifest.json")
    assert manifest["device"] == {}
    assert [a["slug"] for a in manifest["artifacts"]] == ["demo"]

    peers = read_json(cfg.output_dir / "peers.json")
    assert peers["peers"] == []


def test_run_once_creates_output_dir(cfg):
    assert not cfg.output_dir.exists()
    run_once(cfg, get_status_fn=lambda s: (None, []), fetcher=lambda d, t: None)
    assert cfg.output_dir.is_dir()


def test_run_once_leaves_no_temp_files(cfg):
    run_once(cfg, get_status_fn=lambda s: (SELF, []), fetcher=lambda d, t: None)
    names = sorted(p.name for p in cfg.output_dir.iterdir())
    assert names == ["manifest.json", "peers.json"]


def test_config_defaults():
    cfg = Config.from_env({})
    assert str(cfg.artifacts_dir) == "/artifacts"
    assert str(cfg.output_dir) == "/data"
    assert cfg.interval == 120.0
    assert cfg.fetch_timeout == 5.0
    assert cfg.socket_path == "/var/run/tailscale/tailscaled.sock"
    assert str(cfg.mesh_config_path) == "/config/mesh.json"


def test_config_from_env():
    cfg = Config.from_env(
        {
            "DISCOVERY_ARTIFACTS_DIR": "/somewhere/artifacts",
            "DISCOVERY_OUTPUT_DIR": "/somewhere/out",
            "DISCOVERY_INTERVAL": "30",
            "DISCOVERY_FETCH_TIMEOUT": "2.5",
            "TS_SOCKET": "/tmp/tailscaled.sock",
            "MESH_CONFIG_PATH": "/somewhere/mesh.json",
        }
    )
    assert str(cfg.artifacts_dir) == "/somewhere/artifacts"
    assert str(cfg.output_dir) == "/somewhere/out"
    assert cfg.interval == 30.0
    assert cfg.fetch_timeout == 2.5
    assert cfg.socket_path == "/tmp/tailscaled.sock"
    assert str(cfg.mesh_config_path) == "/somewhere/mesh.json"


def test_config_invalid_numbers_fall_back_to_defaults():
    cfg = Config.from_env({"DISCOVERY_INTERVAL": "soon", "DISCOVERY_FETCH_TIMEOUT": "-3"})
    assert cfg.interval == 120.0
    assert cfg.fetch_timeout == 5.0
