"""Internal HTTP API for SSO-gated mesh administration."""

import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from discovery.config import Config
from discovery.mesh_config import (
    ConfigStore,
    ConfigValidationError,
    RevisionConflict,
    mesh_config_to_dict,
    parse_mesh_config,
)

MAX_REQUEST_BYTES = 256 * 1024


def _handler_class(cfg: Config, controller, config_store: ConfigStore):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ArtifactManagement/1"

        def log_message(self, format, *args):
            return

        def _json(self, status: int, body: object, *, etag: str | None = None):
            payload = json.dumps(body, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            if etag is not None:
                self.send_header("ETag", f'"{etag}"')
            self.end_headers()
            self.wfile.write(payload)

        def _authorized(self) -> bool:
            supplied = self.headers.get("Authorization", "")
            expected = f"Bearer {cfg.management_api_token}"
            if not cfg.management_api_token or not hmac.compare_digest(supplied, expected):
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return False
            return True

        def _config_response(self, status: int):
            document = config_store.load()
            self._json(
                status,
                {
                    "config": mesh_config_to_dict(document.config),
                    "revision": document.revision,
                    "discovered_peers": controller.discovered_peers(),
                },
                etag=document.revision,
            )

        def do_GET(self):
            if self.path == "/healthz":
                self._json(HTTPStatus.OK, {"status": "ok"})
            elif self.path == "/api/admin/config":
                if self._authorized():
                    self._config_response(HTTPStatus.OK)
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_PUT(self):
            if self.path != "/api/admin/config":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            if not self._authorized():
                return
            if self.headers.get_content_type() != "application/json":
                self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "JSON required"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_REQUEST_BYTES:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request too large"})
                return
            revision = self.headers.get("If-Match")
            if revision is None:
                self._json(
                    HTTPStatus.PRECONDITION_REQUIRED,
                    {"error": "If-Match revision required"},
                )
                return
            revision = revision.strip('"')
            try:
                raw = json.loads(self.rfile.read(length))
                document = parse_mesh_config(raw)
                saved = config_store.save(document, revision)
            except (json.JSONDecodeError, UnicodeError, ConfigValidationError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            except RevisionConflict as exc:
                self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
                return
            controller.trigger()
            self._json(
                HTTPStatus.OK,
                {
                    "config": mesh_config_to_dict(saved.config),
                    "revision": saved.revision,
                    "discovered_peers": controller.discovered_peers(),
                },
                etag=saved.revision,
            )

        def do_POST(self):
            if self.path != "/api/admin/discover":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            if not self._authorized():
                return
            accepted = controller.trigger()
            self._json(
                HTTPStatus.ACCEPTED if accepted else HTTPStatus.CONFLICT,
                {"status": "accepted" if accepted else "already-pending"},
            )

    return Handler


def create_server(
    cfg: Config,
    controller,
    address: tuple[str, int] | None = None,
    config_store: ConfigStore | None = None,
) -> ThreadingHTTPServer:
    """Create, but do not start, the internal management server."""
    bind = address or (cfg.management_host, cfg.management_port)
    store = config_store or ConfigStore(cfg.mesh_config_path)
    return ThreadingHTTPServer(bind, _handler_class(cfg, controller, store))
