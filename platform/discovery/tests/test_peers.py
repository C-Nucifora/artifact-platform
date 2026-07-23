"""Tests for aggregating peer manifests into peers.json."""

import time

from discovery.peers import build_peers
from discovery.tailnet import Device


def dev(name):
    return Device(hostname=name, dns_name=f"{name}.tail1234.ts.net", ips=(f"100.64.0.{1}",))


def manifest_for(name):
    return {
        "version": 1,
        "device": {"hostname": name},
        "artifacts": [{"slug": f"{name}-app", "title": name, "description": "", "path": "/x/"}],
    }


def test_successful_peers_included():
    devices = [dev("pi"), dev("laptop")]

    def fetcher(device, timeout):
        return manifest_for(device.hostname)

    doc = build_peers(devices, fetcher=fetcher, timeout=1.0)
    assert [p["hostname"] for p in doc["peers"]] == ["laptop", "pi"]  # sorted by dns_name
    assert doc["peers"][0]["dns_name"] == "laptop.tail1234.ts.net"
    assert doc["peers"][0]["url"] == "https://laptop.tail1234.ts.net"
    assert doc["peers"][0]["artifacts"] == manifest_for("laptop")["artifacts"]


def test_failed_peers_silently_skipped():
    devices = [dev("good"), dev("timeout"), dev("garbage")]

    def fetcher(device, timeout):
        if device.hostname == "good":
            return manifest_for("good")
        return None  # fetch_manifest maps timeouts/404s/garbage to None

    doc = build_peers(devices, fetcher=fetcher, timeout=1.0)
    assert [p["hostname"] for p in doc["peers"]] == ["good"]


def test_fetcher_exception_treated_as_failure():
    devices = [dev("good"), dev("explodes")]

    def fetcher(device, timeout):
        if device.hostname == "explodes":
            raise RuntimeError("bug in fetcher")
        return manifest_for("good")

    doc = build_peers(devices, fetcher=fetcher, timeout=1.0)
    assert [p["hostname"] for p in doc["peers"]] == ["good"]


def test_no_peers_yields_empty_list():
    doc = build_peers([], fetcher=lambda d, t: None, timeout=1.0)
    assert doc["peers"] == []
    assert doc["version"] == 1


def test_generated_at_is_iso8601_utc():
    doc = build_peers([], fetcher=lambda d, t: None, timeout=1.0)
    assert doc["generated_at"].endswith("+00:00") or doc["generated_at"].endswith("Z")


def test_hung_fetcher_does_not_hang_build_peers():
    devices = [dev("fast"), dev("stuck")]

    def fetcher(device, timeout):
        if device.hostname == "stuck":
            time.sleep(10)  # simulates a fetch that ignores its timeout
            return manifest_for("stuck")
        return manifest_for("fast")

    start = time.monotonic()
    doc = build_peers(devices, fetcher=fetcher, timeout=0.1, deadline=0.5)
    elapsed = time.monotonic() - start
    assert elapsed < 5.0
    assert [p["hostname"] for p in doc["peers"]] == ["fast"]


def test_artifacts_missing_from_manifest_defaults_to_empty():
    # build_peers trusts fetch_manifest's validation, but degrade gracefully anyway
    doc = build_peers([dev("odd")], fetcher=lambda d, t: {"version": 1}, timeout=1.0)
    assert doc["peers"][0]["artifacts"] == []
