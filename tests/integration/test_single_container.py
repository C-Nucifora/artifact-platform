import json
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:18767"


def request(path):
    try:
        with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=5) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


def test_single_container_serves_catalog_and_manifest():
    status, body, _ = request("/")
    assert status == 200
    assert b"Artifact" in body

    status, body, headers = request("/manifest.json")
    assert status == 200
    assert headers["Cache-Control"] == "no-cache"
    assert json.loads(body)["version"] == 1


def test_single_container_keeps_admin_hidden_without_sso():
    for path in ("/admin", "/admin.html", "/api/admin/config", "/oauth2/start"):
        status, _, _ = request(path)
        assert status == 404
