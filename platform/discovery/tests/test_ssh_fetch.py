import json
import subprocess

from discovery.mesh import ResolvedPeer
from discovery.ssh_fetch import MAX_MANIFEST_BYTES, fetch_manifest_ssh


def peer(target="pi.tail1234.ts.net"):
    return ResolvedPeer(
        peer_id="pi.tail1234.ts.net",
        hostname="pi",
        dns_name="pi.tail1234.ts.net",
        ssh_target=target,
        public_url="https://pi.example.com",
        source="discovered",
        online=True,
        excluded_artifacts=(),
    )


def test_fetch_uses_tailscale_ssh_without_a_shell():
    seen = {}

    def runner(argv, timeout):
        seen["argv"] = argv
        seen["timeout"] = timeout
        return json.dumps({"version": 1, "artifacts": []})

    result = fetch_manifest_ssh(peer(), "/run/tailscale.sock", 2.5, runner=runner)

    assert result == {"version": 1, "artifacts": []}
    assert seen == {
        "argv": [
            "tailscale",
            "--socket",
            "/run/tailscale.sock",
            "ssh",
            "artifact@pi.tail1234.ts.net",
            "cat",
            "/generated/manifest.json",
        ],
        "timeout": 2.5,
    }


def test_fetch_rejects_non_object_or_missing_artifacts():
    for payload in ("[]", '{"version": 1}', '{"artifacts": {}}'):
        assert fetch_manifest_ssh(peer(), "/sock", 1, runner=lambda a, t, p=payload: p) is None


def test_fetch_rejects_oversized_output():
    payload = " " * MAX_MANIFEST_BYTES + "{}"

    assert fetch_manifest_ssh(peer(), "/sock", 1, runner=lambda a, t: payload) is None


def test_fetch_maps_command_failures_to_none():
    failures = (
        subprocess.CalledProcessError(1, ["tailscale"]),
        subprocess.TimeoutExpired(["tailscale"], 1),
        OSError("missing client"),
    )
    for failure in failures:

        def runner(argv, timeout, exc=failure):
            raise exc

        assert fetch_manifest_ssh(peer(), "/sock", 1, runner=runner) is None


def test_fetch_rejects_invalid_json():
    assert fetch_manifest_ssh(peer(), "/sock", 1, runner=lambda a, t: "not json") is None
