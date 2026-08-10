"""Tests for aggregating peer manifests into peers.json."""

import time

from discovery.mesh import ResolvedPeer
from discovery.peers import build_peers


def dev(name):
    return resolved(name)


def manifest_for(name):
    return {
        "version": 1,
        "device": {"hostname": name},
        "artifacts": [
            {
                "slug": f"{name}-app",
                "title": name,
                "description": "",
                "path": f"/artifacts/{name}-app/",
            }
        ],
    }


def resolved(name, excluded_artifacts=()):
    return ResolvedPeer(
        peer_id=f"{name}.tail1234.ts.net",
        hostname=name,
        dns_name=f"{name}.tail1234.ts.net",
        ssh_target=f"{name}.tail1234.ts.net",
        public_url=f"https://{name}.example.com",
        source="discovered",
        online=True,
        excluded_artifacts=excluded_artifacts,
    )


def test_version_two_peer_output_uses_resolved_public_fields():
    doc = build_peers(
        [resolved("pi")],
        fetcher=lambda peer, socket, timeout: manifest_for("pi"),
        timeout=1.0,
        socket_path="/sock",
    )

    assert doc["version"] == 2
    assert doc["peers"][0]["url"] == "https://pi.example.com"
    assert doc["peers"][0]["source"] == "discovered"
    assert doc["peers"][0]["state"] == "online"
    assert "ssh_target" not in doc["peers"][0]


def test_resolved_artifact_exclusions_are_not_published():
    doc = build_peers(
        [resolved("pi", excluded_artifacts=("pi-app",))],
        fetcher=lambda peer, socket, timeout: manifest_for("pi"),
        timeout=1.0,
        socket_path="/sock",
    )

    assert doc["peers"][0]["artifacts"] == []


def test_successful_peers_included():
    devices = [dev("pi"), dev("laptop")]

    def fetcher(device, socket, timeout):
        return manifest_for(device.hostname)

    doc = build_peers(devices, fetcher=fetcher, timeout=1.0, socket_path="/sock")
    assert [p["hostname"] for p in doc["peers"]] == ["laptop", "pi"]  # sorted by dns_name
    assert doc["peers"][0]["dns_name"] == "laptop.tail1234.ts.net"
    assert doc["peers"][0]["url"] == "https://laptop.example.com"
    assert doc["peers"][0]["artifacts"] == manifest_for("laptop")["artifacts"]


def test_failed_peers_silently_skipped():
    devices = [dev("good"), dev("timeout"), dev("garbage")]

    def fetcher(device, socket, timeout):
        if device.hostname == "good":
            return manifest_for("good")
        return None  # fetch_manifest maps timeouts/404s/garbage to None

    doc = build_peers(devices, fetcher=fetcher, timeout=1.0, socket_path="/sock")
    assert [p["hostname"] for p in doc["peers"]] == ["good"]


def test_fetcher_exception_treated_as_failure():
    devices = [dev("good"), dev("explodes")]

    def fetcher(device, socket, timeout):
        if device.hostname == "explodes":
            raise RuntimeError("bug in fetcher")
        return manifest_for("good")

    doc = build_peers(devices, fetcher=fetcher, timeout=1.0, socket_path="/sock")
    assert [p["hostname"] for p in doc["peers"]] == ["good"]


def test_no_peers_yields_empty_list():
    doc = build_peers([], fetcher=lambda p, s, t: None, timeout=1.0, socket_path="/sock")
    assert doc["peers"] == []
    assert doc["version"] == 2


def test_generated_at_is_iso8601_utc():
    doc = build_peers([], fetcher=lambda p, s, t: None, timeout=1.0, socket_path="/sock")
    assert doc["generated_at"].endswith("+00:00") or doc["generated_at"].endswith("Z")


def test_hung_fetcher_does_not_hang_build_peers():
    devices = [dev("fast"), dev("stuck")]

    def fetcher(device, socket, timeout):
        if device.hostname == "stuck":
            time.sleep(10)  # simulates a fetch that ignores its timeout
            return manifest_for("stuck")
        return manifest_for("fast")

    start = time.monotonic()
    doc = build_peers(devices, fetcher=fetcher, timeout=0.1, socket_path="/sock", deadline=0.5)
    elapsed = time.monotonic() - start
    assert elapsed < 5.0
    assert [p["hostname"] for p in doc["peers"]] == ["fast"]


def test_artifacts_missing_from_manifest_defaults_to_empty():
    # build_peers trusts fetch_manifest's validation, but degrade gracefully anyway
    doc = build_peers(
        [dev("odd")],
        fetcher=lambda p, s, t: {"version": 1},
        timeout=1.0,
        socket_path="/sock",
    )
    assert doc["peers"][0]["artifacts"] == []


def peer_serving(artifacts):
    return build_peers(
        [dev("hostile")],
        fetcher=lambda p, s, t: {"version": 1, "artifacts": artifacts},
        timeout=1.0,
        socket_path="/sock",
    )["peers"][0]["artifacts"]


def test_peer_supplied_path_is_never_trusted():
    # "@evil.example" concatenated onto https://host would resolve to evil.example
    entries = peer_serving([{"slug": "ok", "title": "OK", "path": "@evil.example"}])
    assert entries[0]["path"] == "/artifacts/ok/"


def test_entries_with_bad_slugs_dropped():
    entries = peer_serving(
        [
            {"slug": "../../etc/passwd"},
            {"slug": "Has Spaces"},
            {"slug": "UPPER"},
            {"slug": "-leading-hyphen"},
            {"slug": ""},
            {"slug": "good-one"},
        ]
    )
    assert [e["slug"] for e in entries] == ["good-one"]


def test_non_dict_entries_dropped():
    entries = peer_serving([None, "a string", 42, ["nested"], {"slug": "survivor"}])
    assert [e["slug"] for e in entries] == ["survivor"]


def test_missing_slug_dropped():
    assert peer_serving([{"title": "No slug here"}]) == []


def test_non_string_text_falls_back():
    entries = peer_serving([{"slug": "thing", "title": 42, "description": ["x"]}])
    assert entries[0]["title"] == "thing"
    assert entries[0]["description"] == ""


def test_long_text_truncated():
    entries = peer_serving([{"slug": "thing", "title": "T" * 5000, "description": "D" * 5000}])
    assert len(entries[0]["title"]) == 300
    assert len(entries[0]["description"]) == 300


def test_artifact_count_capped():
    entries = peer_serving([{"slug": f"a{i}"} for i in range(500)])
    assert len(entries) == 200


def test_artifacts_not_a_list_yields_empty():
    assert peer_serving("not a list") == []


def test_sanitized_entry_shape_is_exact():
    entries = peer_serving([{"slug": "x", "title": "X", "description": "D", "evil": "<script>"}])
    assert entries[0] == {
        "slug": "x",
        "title": "X",
        "description": "D",
        "path": "/artifacts/x/",
    }
