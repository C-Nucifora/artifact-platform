"""HTTP boundary tests for the optional OIDC-protected deployment."""

import json
import os
import time
import urllib.error
import urllib.request

import pytest

BASE_URL = os.environ.get("ARTIFACT_SSO_TEST_URL", "http://127.0.0.1:8481")


def get(path, *, cookie=None, extra_headers=None):
    headers = dict(extra_headers or {})
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(BASE_URL + path, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


@pytest.fixture(scope="session", autouse=True)
def wait_for_stack():
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            if get("/")[0] == 200:
                return
        except OSError:
            pass
        time.sleep(1)
    pytest.fail("SSO integration stack did not become reachable")


def test_public_catalog_remains_anonymous():
    status, _, body = get("/")

    assert status == 200
    assert b"Artifact<br>mesh" in body


def test_anonymous_and_non_admin_users_cannot_reach_admin():
    anonymous, _, _ = get("/admin")
    member, _, _ = get("/admin", cookie="stub_session=member")

    assert anonymous == 401
    assert member == 403


def test_spoofed_identity_headers_do_not_bypass_auth():
    status, _, _ = get(
        "/admin",
        extra_headers={"X-Auth-Request-Groups": "artifact-platform-admins"},
    )

    assert status == 401


def test_admin_user_reaches_admin_page_and_api():
    page_status, _, page_body = get("/admin", cookie="stub_session=admin")
    api_status, headers, api_body = get(
        "/api/admin/config", cookie="stub_session=admin"
    )

    assert page_status == 200
    assert b"Mesh configuration" in page_body
    assert api_status == 200
    assert headers.get_content_type() == "application/json"
    assert json.loads(api_body)["config"]["version"] == 1


def test_oauth_callback_namespace_reaches_auth_gateway():
    status, _, body = get("/oauth2/start")

    assert status == 200
    assert body == b"stub oauth endpoint"
