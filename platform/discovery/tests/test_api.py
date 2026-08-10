import http.client
import json
import threading

import pytest

from discovery.api import create_server
from discovery.config import Config


class Controller:
    def __init__(self):
        self.trigger_count = 0

    def trigger(self):
        self.trigger_count += 1
        return True

    def discovered_peers(self):
        return [{"hostname": "pi", "dns_name": "pi.tail1234.ts.net", "online": True}]


@pytest.fixture
def api(tmp_path):
    mesh_path = tmp_path / "mesh.json"
    mesh_path.write_text('{"version": 1}', encoding="utf-8")
    cfg = Config(
        artifacts_dir=tmp_path / "artifacts",
        output_dir=tmp_path / "output",
        interval=120,
        fetch_timeout=5,
        socket_path="/sock",
        mesh_config_path=mesh_path,
        management_api_token="correct-secret",
    )
    controller = Controller()
    server = create_server(cfg, controller, ("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address, controller, mesh_path
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def request(address, method, path, *, token=None, body=None, headers=None):
    conn = http.client.HTTPConnection(*address, timeout=2)
    request_headers = dict(headers or {})
    if token is not None:
        request_headers["Authorization"] = f"Bearer {token}"
    encoded = None
    if body is not None:
        encoded = json.dumps(body).encode()
        request_headers["Content-Type"] = "application/json"
    conn.request(method, path, body=encoded, headers=request_headers)
    response = conn.getresponse()
    payload = response.read()
    conn.close()
    parsed = json.loads(payload) if payload else None
    return response.status, dict(response.headers), parsed


def test_health_does_not_require_authentication(api):
    address, _, _ = api

    status, headers, body = request(address, "GET", "/healthz")

    assert status == 200
    assert body == {"status": "ok"}
    assert headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize("token", [None, "wrong-secret"])
def test_admin_routes_reject_missing_or_wrong_token(api, token):
    address, _, _ = api

    status, _, body = request(address, "GET", "/api/admin/config", token=token)

    assert status == 401
    assert body == {"error": "unauthorized"}


def test_get_returns_normalized_config_revision_and_discovery(api):
    address, _, _ = api

    status, headers, body = request(address, "GET", "/api/admin/config", token="correct-secret")

    assert status == 200
    assert body["config"] == {"version": 1, "excluded_peers": [], "peers": {}}
    assert body["revision"] == headers["ETag"].strip('"')
    assert body["discovered_peers"][0]["dns_name"] == "pi.tail1234.ts.net"


def test_put_requires_revision(api):
    address, _, _ = api

    status, _, body = request(
        address, "PUT", "/api/admin/config", token="correct-secret", body={"version": 1}
    )

    assert status == 428
    assert body == {"error": "If-Match revision required"}


def test_put_validates_and_atomically_saves(api):
    address, _, path = api
    _, headers, _ = request(address, "GET", "/api/admin/config", token="correct-secret")

    status, response_headers, body = request(
        address,
        "PUT",
        "/api/admin/config",
        token="correct-secret",
        body={"version": 1, "excluded_peers": ["pi.tail1234.ts.net"]},
        headers={"If-Match": headers["ETag"]},
    )

    assert status == 200
    assert body["config"]["excluded_peers"] == ["pi.tail1234.ts.net"]
    assert response_headers["ETag"].strip('"') == body["revision"]
    assert json.loads(path.read_text())["excluded_peers"] == ["pi.tail1234.ts.net"]


def test_put_reports_invalid_config_and_stale_revision(api):
    address, _, _ = api

    invalid_status, _, _ = request(
        address,
        "PUT",
        "/api/admin/config",
        token="correct-secret",
        body={"version": 1, "unexpected": True},
        headers={"If-Match": '"stale"'},
    )
    stale_status, _, _ = request(
        address,
        "PUT",
        "/api/admin/config",
        token="correct-secret",
        body={"version": 1},
        headers={"If-Match": '"stale"'},
    )

    assert invalid_status == 400
    assert stale_status == 409


def test_discover_triggers_a_bounded_background_pass(api):
    address, controller, _ = api

    status, _, body = request(address, "POST", "/api/admin/discover", token="correct-secret")

    assert status == 202
    assert body == {"status": "accepted"}
    assert controller.trigger_count == 1


def test_unknown_route_and_oversized_body_are_rejected(api):
    address, _, _ = api
    missing_status, _, _ = request(address, "GET", "/unknown")

    conn = http.client.HTTPConnection(*address, timeout=2)
    conn.request(
        "PUT",
        "/api/admin/config",
        body=b"x",
        headers={
            "Authorization": "Bearer correct-secret",
            "Content-Type": "application/json",
            "Content-Length": str(300 * 1024),
        },
    )
    response = conn.getresponse()
    response.read()
    conn.close()

    assert missing_status == 404
    assert response.status == 413
