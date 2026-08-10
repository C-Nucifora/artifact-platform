"""Deterministic forward-auth stub used only by the SSO integration stack."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/oauth2/auth":
            cookie = self.headers.get("Cookie", "")
            if "stub_session=admin" in cookie:
                self.send_response(202)
                self.send_header("X-Auth-Request-User", "admin")
                self.send_header("X-Auth-Request-Email", "admin@example.com")
                self.send_header("X-Auth-Request-Groups", "artifact-platform-admins")
            elif "stub_session=member" in cookie:
                self.send_response(403)
            else:
                self.send_response(401)
            self.end_headers()
            return
        if self.path.startswith("/oauth2/"):
            body = b"stub oauth endpoint"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


ThreadingHTTPServer(("0.0.0.0", 4180), Handler).serve_forever()
