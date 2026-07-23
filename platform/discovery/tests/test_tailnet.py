"""Tests for parsing `tailscale status --json` into self + online peers."""

import json
import subprocess
from pathlib import Path

import pytest

from discovery.tailnet import Device, TailnetError, get_status

FIXTURE = (Path(__file__).parent / "fixtures" / "status.json").read_text()


def runner_returning(text):
    def runner(socket_path, timeout):
        return text

    return runner


def runner_raising(exc):
    def runner(socket_path, timeout):
        raise exc

    return runner


def test_parses_self_device():
    self_dev, _ = get_status("/tmp/sock", runner=runner_returning(FIXTURE))
    assert self_dev == Device(
        hostname="studio",
        dns_name="studio.tail1234.ts.net",
        ips=("100.64.0.1", "fd7a:115c:a1e0::1"),
    )


def test_only_online_peers_with_dns_names():
    _, peers = get_status("/tmp/sock", runner=runner_returning(FIXTURE))
    assert [p.dns_name for p in peers] == ["pi.tail1234.ts.net"]
    assert peers[0].hostname == "pi"
    assert peers[0].ips == ("100.64.0.2", "fd7a:115c:a1e0::2")


def test_trailing_dot_stripped_from_dns_names():
    self_dev, peers = get_status("/tmp/sock", runner=runner_returning(FIXTURE))
    assert not self_dev.dns_name.endswith(".")
    assert all(not p.dns_name.endswith(".") for p in peers)


def test_no_peer_key_yields_empty_list():
    status = json.loads(FIXTURE)
    del status["Peer"]
    _, peers = get_status("/tmp/sock", runner=runner_returning(json.dumps(status)))
    assert peers == []


def test_null_peer_map_yields_empty_list():
    status = json.loads(FIXTURE)
    status["Peer"] = None
    _, peers = get_status("/tmp/sock", runner=runner_returning(json.dumps(status)))
    assert peers == []


def test_peer_missing_ips_gets_empty_tuple():
    status = json.loads(FIXTURE)
    peer_key = next(iter(status["Peer"]))
    del status["Peer"][peer_key]["TailscaleIPs"]
    _, peers = get_status("/tmp/sock", runner=runner_returning(json.dumps(status)))
    assert peers[0].ips == ()


def test_self_without_dns_name_is_none():
    status = json.loads(FIXTURE)
    status["Self"]["DNSName"] = ""
    self_dev, _ = get_status("/tmp/sock", runner=runner_returning(json.dumps(status)))
    assert self_dev is None


def test_missing_binary_raises_tailnet_error():
    with pytest.raises(TailnetError):
        get_status("/tmp/sock", runner=runner_raising(FileNotFoundError("tailscale")))


def test_command_failure_raises_tailnet_error():
    exc = subprocess.CalledProcessError(1, ["tailscale"], stderr="no daemon")
    with pytest.raises(TailnetError):
        get_status("/tmp/sock", runner=runner_raising(exc))


def test_command_timeout_raises_tailnet_error():
    exc = subprocess.TimeoutExpired(["tailscale"], 10)
    with pytest.raises(TailnetError):
        get_status("/tmp/sock", runner=runner_raising(exc))


def test_invalid_json_raises_tailnet_error():
    with pytest.raises(TailnetError):
        get_status("/tmp/sock", runner=runner_returning("garbage{"))


def test_non_object_json_raises_tailnet_error():
    with pytest.raises(TailnetError):
        get_status("/tmp/sock", runner=runner_returning('["not", "a", "status"]'))
