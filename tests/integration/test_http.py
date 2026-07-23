"""HTTP integration tests against the Caddy test stack.

Bring the stack up first:
    docker compose -f docker-compose.test.yml up -d --wait

The stack serves the real Caddyfile and index site with fixture artifacts and
fixture generated JSON, on http://127.0.0.1:8480 (override: ARTIFACT_TEST_URL,
matching ARTIFACT_TEST_PORT on the compose side).
"""

import json
import os
import time
import urllib.error
import urllib.request

import pytest

BASE_URL = os.environ.get("ARTIFACT_TEST_URL", "http://127.0.0.1:8480")


def get(path):
    """Return (status, headers, body_bytes) without raising on HTTP errors."""
    try:
        with urllib.request.urlopen(BASE_URL + path, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read()


@pytest.fixture(scope="session", autouse=True)
def wait_for_stack():
    deadline = time.monotonic() + 30
    last_error = None
    while time.monotonic() < deadline:
        try:
            status, _, _ = get("/")
            if status == 200:
                return
            last_error = f"HTTP {status}"
        except OSError as err:
            last_error = err
        time.sleep(1)
    pytest.fail(
        f"test stack not reachable at {BASE_URL} ({last_error}); "
        "did you run: docker compose -f docker-compose.test.yml up -d --wait"
    )


def test_index_page():
    status, headers, body = get("/")
    assert status == 200
    assert headers.get_content_type() == "text/html"
    assert b"Artifacts" in body


def test_manifest_json():
    status, headers, body = get("/manifest.json")
    assert status == 200
    assert headers.get_content_type() == "application/json"
    assert "no-cache" in (headers.get("Cache-Control") or "")
    manifest = json.loads(body)
    assert [a["slug"] for a in manifest["artifacts"]] == ["demo", "no-meta"]


def test_peers_json():
    status, headers, body = get("/peers.json")
    assert status == 200
    assert headers.get_content_type() == "application/json"
    assert "no-cache" in (headers.get("Cache-Control") or "")
    peers = json.loads(body)
    assert peers["peers"][0]["dns_name"] == "otherbox.tail1234.ts.net"


def test_artifact_with_index_served():
    status, headers, body = get("/artifacts/demo/")
    assert status == 200
    assert headers.get_content_type() == "text/html"
    assert b"demo artifact fixture" in body


def test_artifact_without_trailing_slash_redirects():
    status, headers, _ = get("/artifacts/demo")
    # file_server canonicalizes directory URLs with a redirect
    assert status == 200  # urllib follows the redirect
    _, _, body = get("/artifacts/demo")
    assert b"demo artifact fixture" in body


def test_artifact_asset_content_type():
    status, headers, body = get("/artifacts/demo/meta.json")
    assert status == 200
    assert headers.get_content_type() == "application/json"
    assert json.loads(body)["title"] == "Demo"


def test_artifacts_directory_listing():
    status, headers, body = get("/artifacts/")
    assert status == 200
    assert headers.get_content_type() == "text/html"
    assert b"demo" in body
    assert b"no-meta" in body


def test_second_artifact_served():
    status, _, body = get("/artifacts/no-meta/")
    assert status == 200
    assert b"artifact without meta.json" in body


def test_unknown_path_404s():
    status, _, _ = get("/definitely-not-a-thing")
    assert status == 404


def test_unknown_artifact_404s():
    status, _, _ = get("/artifacts/ghost/")
    assert status == 404
