# Artifact Platform Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a technical artifact control plane with keyless Tailscale SSH meshing, editable peer policy, an optional Authentik-compatible SSO admin scope, a polished responsive UI, and enforced GitHub CI.

**Architecture:** The Python discovery container owns manifest generation, SSH peer synchronization, normalized mesh configuration, and an internal admin API. Caddy serves public assets and, only in the SSO Compose overlay, proxies protected admin routes through OAuth2 Proxy. Tailscale provides node discovery, SSH identity, and Funnel delivery.

**Tech Stack:** Python 3.13 standard library, pytest, Ruff, Docker Compose, Tailscale, Caddy 2, OAuth2 Proxy, HTML/CSS/vanilla JavaScript, Playwright, GitHub Actions.

## Global Constraints

- No user-generated or user-distributed SSH keys; automated peer reads use Tailscale SSH node identity.
- Default behavior is a full mesh of eligible online peers.
- The config file is authoritative and admin writes are validated, revision-checked, and atomic.
- Base mode exposes no admin page, admin API, or OAuth callback route.
- SSO uses generic OIDC and must work with Authentik.
- Public peer documents never expose SSH targets, raw errors, secrets, exclusions, or identity headers.
- Public URLs must be HTTPS; peer identifiers, SSH targets, and artifact slugs are strictly validated.
- The frontend uses no framework or bundler and meets keyboard, reduced-motion, responsive, and AA contrast requirements.
- Git commits contain no AI authorship references.

---

### Task 1: Versioned mesh configuration

**Files:**
- Create: `config/mesh.json`
- Create: `platform/discovery/discovery/mesh_config.py`
- Create: `platform/discovery/tests/test_mesh_config.py`
- Modify: `platform/discovery/discovery/config.py`

**Interfaces:**
- Produces: `MeshConfig`, `PeerRule`, `ConfigDocument`, `load_mesh_config(path)`, `parse_mesh_config(raw)`, and `save_mesh_config(path, document, expected_revision)`.
- `ConfigDocument.revision` is the SHA-256 hex digest of canonical JSON; `ConfigDocument.config` is normalized `MeshConfig`.

- [ ] **Step 1: Write failing configuration tests**

Cover an empty version-1 document, strict peer/slug/HTTPS validation, unknown-field rejection through `parse_mesh_config`, tolerant fallback through `load_mesh_config`, canonical revision stability, mismatch rejection, and atomic replacement.

```python
def test_save_rejects_stale_revision(tmp_path):
    path = tmp_path / "mesh.json"
    first = save_mesh_config(path, parse_mesh_config({"version": 1}), None)
    with pytest.raises(RevisionConflict):
        save_mesh_config(path, parse_mesh_config({"version": 1}), "stale")
    assert load_mesh_config(path).revision == first.revision
```

- [ ] **Step 2: Run the new tests and verify failure**

Run: `cd platform/discovery && uv run --group dev pytest tests/test_mesh_config.py -q`

Expected: collection fails because `discovery.mesh_config` does not exist.

- [ ] **Step 3: Implement the normalized model and atomic store**

Use frozen dataclasses, exact key sets, `urllib.parse.urlsplit`, existing slug constraints, canonical `json.dumps(..., sort_keys=True, separators=(",", ":"))`, a same-directory temporary file, `os.fsync`, and `os.replace`. Add `mesh_config_path: Path` to `Config` with `MESH_CONFIG_PATH=/config/mesh.json` default.

- [ ] **Step 4: Run focused and existing unit tests**

Run: `cd platform/discovery && uv run --group dev pytest tests/test_mesh_config.py tests/test_config.py -q`

Expected: all pass.

- [ ] **Step 5: Commit and push**

```bash
git add config/mesh.json platform/discovery/discovery/config.py platform/discovery/discovery/mesh_config.py platform/discovery/tests
git commit -m "Add versioned mesh configuration"
git push origin HEAD
```

### Task 2: Tailscale SSH manifest transport and mesh resolution

**Files:**
- Create: `platform/discovery/discovery/ssh_fetch.py`
- Create: `platform/discovery/discovery/mesh.py`
- Create: `platform/discovery/tests/test_ssh_fetch.py`
- Create: `platform/discovery/tests/test_mesh.py`
- Modify: `platform/discovery/discovery/loop.py`
- Modify: `platform/discovery/discovery/peers.py`
- Modify: `platform/discovery/tests/test_loop.py`
- Delete: `platform/discovery/discovery/fetch.py`
- Delete: `platform/discovery/tests/test_fetch.py`

**Interfaces:**
- Consumes: `MeshConfig`, `PeerRule`, and `Device`.
- Produces: `ResolvedPeer`, `resolve_peers(devices, config)`, and `fetch_manifest_ssh(peer, socket_path, timeout, runner=...) -> dict | None`.
- The SSH argv is `tailscale --socket <socket> ssh artifact@<target> cat /generated/manifest.json`; subprocess timeout and JSON shape limits are mandatory.

- [ ] **Step 1: Write failing SSH transport tests**

Assert exact argv, no shell execution, timeout propagation into `subprocess.run`, maximum output enforcement, valid object parsing, and graceful `None` for nonzero exit, timeout, invalid JSON, arrays, or oversized output.

- [ ] **Step 2: Run the SSH tests and verify failure**

Run: `cd platform/discovery && uv run --group dev pytest tests/test_ssh_fetch.py -q`

Expected: collection fails because `discovery.ssh_fetch` does not exist.

- [ ] **Step 3: Implement SSH fetching**

Use `subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=True)` with no shell. Cap accepted stdout at 1 MiB and require a JSON object containing an artifact list.

- [ ] **Step 4: Write failing mesh-resolution tests**

Cover default-all discovery, exclusions before fetch, manual peers, SSH/public overrides, invalid/offline public state, artifact exclusions, and deterministic ordering.

- [ ] **Step 5: Implement mesh resolution and connect the loop**

Resolve discovered and manual records into immutable `ResolvedPeer` values. Update `build_peers` to receive resolved peers and emit version 2 safe fields. Load config once per cycle; call SSH fetcher concurrently through the existing bounded executor.

- [ ] **Step 6: Run discovery tests**

Run: `cd platform/discovery && uv run --group dev pytest -q`

Expected: all tests pass and no HTTP fetch module remains referenced.

- [ ] **Step 7: Commit and push**

```bash
git add platform/discovery
git commit -m "Discover peer manifests over Tailscale SSH"
git push origin HEAD
```

### Task 3: Internal management API

**Files:**
- Create: `platform/discovery/discovery/api.py`
- Create: `platform/discovery/discovery/service.py`
- Create: `platform/discovery/tests/test_api.py`
- Modify: `platform/discovery/discovery/__main__.py`
- Modify: `platform/discovery/discovery/config.py`
- Modify: `platform/discovery/discovery/loop.py`

**Interfaces:**
- Consumes: config load/save functions and a thread-safe `DiscoveryController.trigger()` method.
- Produces: `create_server(config, controller)` serving `GET /healthz`, `GET /api/admin/config`, `PUT /api/admin/config`, and `POST /api/admin/discover`.
- Authorization requires `Authorization: Bearer <MANAGEMENT_API_TOKEN>` using `hmac.compare_digest`.

- [ ] **Step 1: Write failing API tests**

Start the server on an ephemeral loopback port. Assert health without auth; 401 without or with a wrong bearer token; normalized GET response; 428 without `If-Match`; 409 on stale revision; 400 on invalid JSON/config; successful PUT persistence; 202 trigger response; body and content-type limits; and no reflection of spoofed identity headers.

- [ ] **Step 2: Run tests and verify failure**

Run: `cd platform/discovery && uv run --group dev pytest tests/test_api.py -q`

Expected: collection fails because `discovery.api` does not exist.

- [ ] **Step 3: Implement the loopback API and controller**

Use `ThreadingHTTPServer`, a 256 KiB request limit, JSON-only mutations, constant-time bearer comparison, security response headers, structured status codes, and a controller event that wakes the discovery loop without overlapping passes.

- [ ] **Step 4: Run all unit tests**

Run: `cd platform/discovery && uv run --group dev pytest -q`

Expected: all pass.

- [ ] **Step 5: Commit and push**

```bash
git add platform/discovery
git commit -m "Add authenticated mesh management API"
git push origin HEAD
```

### Task 4: Keyless SSH-capable runtime and base routing

**Files:**
- Create: `platform/tailscale/Dockerfile`
- Create: `platform/caddy/Caddyfile.base`
- Create: `platform/caddy/snippets/security.caddy`
- Create: `platform/tailscale/policy.example.hujson`
- Modify: `docker-compose.yml`
- Modify: `docker-compose.test.yml`
- Modify: `.env.example`
- Delete: `platform/caddy/Caddyfile`
- Modify: `tests/integration/test_http.py`

**Interfaces:**
- Tailscale image defines unprivileged user `artifact` and exposes `/generated/manifest.json` read-only to it.
- Discovery mounts `/config/mesh.json` read-write and talks to tailscaled through `/var/run/tailscale/tailscaled.sock`.
- Base Caddy routes only `/`, static assets, manifests, peers, and `/artifacts/*`; `/admin`, `/api/admin/*`, and `/oauth2/*` return 404.

- [ ] **Step 1: Add failing base-mode integration assertions**

Assert admin and OAuth paths return 404, CSP and anti-sniff headers exist, static assets have explicit caching, JSON remains no-cache, and artifacts retain current behavior.

- [ ] **Step 2: Run integration tests and verify failure**

Run: `make integration`

Expected: new route/security assertions fail.

- [ ] **Step 3: Implement the Tailscale image and Compose wiring**

Build from `tailscale/tailscale:stable`, create the `artifact` user, enable Tailscale SSH with containerboot arguments, mount generated data read-only into the sidecar, mount config into discovery, and add API health checks. Preserve loopback preview and Funnel behavior.

- [ ] **Step 4: Implement explicit base Caddy routing**

Use route-specific handlers and the shared security snippet. Deny admin namespaces before the static fallback. Update the test Compose file to use the base configuration.

- [ ] **Step 5: Run build and integration verification**

Run: `make build && make integration`

Expected: Compose validates, images build, and HTTP tests pass.

- [ ] **Step 6: Commit and push**

```bash
git add .env.example docker-compose.yml docker-compose.test.yml platform/caddy platform/tailscale tests/integration
git commit -m "Harden the keyless mesh runtime"
git push origin HEAD
```

### Task 5: Public control-plane visual overhaul

**Files:**
- Create: `platform/site/styles.css`
- Create: `platform/site/app.js`
- Modify: `platform/site/index.html`
- Create: `tests/ui/catalog.spec.js`
- Create: `package.json`
- Create: `playwright.config.js`
- Modify: `tests/integration/test_http.py`

**Interfaces:**
- `app.js` consumes manifest v1 and peers v1/v2 defensively and renders only through DOM APIs using `textContent`.
- Stable selectors use `data-testid` only for status summary, local grid, peer grid, empty state, and degraded state.

- [ ] **Step 1: Add failing static and browser tests**

Assert separate CSS/JS assets, semantic landmarks, no inline script/style, status rail, safe link construction, populated fixtures, responsive layout at 390 px and 1440 px, visible keyboard focus, empty/degraded state behavior, and no horizontal overflow.

- [ ] **Step 2: Run tests and verify failure**

Run: `make integration` and `npm test`

Expected: tests fail because the new assets and interface do not exist.

- [ ] **Step 3: Build semantic HTML and design tokens**

Create a near-black navy system with slate borders, cyan status accents, strong type hierarchy, responsive grid, motion limited behind `prefers-reduced-motion`, explicit focus rings, and reusable state/card styles. Use local/system font stacks only.

- [ ] **Step 4: Implement defensive rendering**

Render node identity, mesh/artifact counts, last sync, local artifacts, peer groups, connection/source badges, empty states, and partial failure. Allow links only when `new URL()` yields HTTPS and artifact paths match the slug pattern.

- [ ] **Step 5: Run HTTP and browser tests**

Run: `make integration && npm test`

Expected: all pass at both viewports.

- [ ] **Step 6: Commit and push**

```bash
git add package.json playwright.config.js platform/site tests
git commit -m "Redesign the artifact control plane"
git push origin HEAD
```

### Task 6: Authentik-compatible SSO admin scope

**Files:**
- Create: `docker-compose.sso.yml`
- Create: `platform/caddy/Caddyfile.sso`
- Create: `platform/oauth2-proxy/oauth2-proxy.cfg`
- Create: `platform/site/admin.html`
- Create: `platform/site/admin.js`
- Create: `tests/integration/stub_auth.py`
- Create: `tests/integration/test_sso_http.py`
- Modify: `platform/site/styles.css`
- Modify: `.env.example`
- Modify: `Makefile`

**Interfaces:**
- OAuth2 Proxy uses generic OIDC discovery and passes verified identity/group headers.
- Caddy strips incoming auth headers, requires the configured admin group, injects the internal bearer token, and proxies admin API traffic.
- `admin.js` uses `GET/PUT /api/admin/config`, preserves the returned ETag, sends `If-Match`, and represents all three peer operations plus artifact exclusions.

- [ ] **Step 1: Write failing SSO routing tests**

Run Caddy with a deterministic stub auth service. Assert anonymous admin requests redirect or return 401, an authenticated non-admin receives 403, an admin reaches HTML/API, spoofed headers are ignored, callback routes reach auth, and public routes remain anonymous.

- [ ] **Step 2: Run tests and verify failure**

Run: `make integration-sso`

Expected: fails because the overlay and SSO routes do not exist.

- [ ] **Step 3: Implement the SSO overlay and protected routes**

Add OAuth2 Proxy with issuer, client, cookie, redirect, and group settings from environment. The overlay publishes the configured site ports/domain and swaps Caddy configuration. Do not add admin routes to base mode.

- [ ] **Step 4: Add failing admin UI browser tests**

Assert peer exclusion/restoration, manual peer entry, endpoint overrides, artifact exclusion, client validation, save/revision conflict feedback, unsaved state, keyboard operation, and confirmation before exclusion.

- [ ] **Step 5: Implement the admin editor**

Use accessible native forms and dialogs, explicit source/status labels, immutable draft updates, URL/target validation matching the backend, optimistic save state, and reload-on-conflict guidance.

- [ ] **Step 6: Run SSO integration and browser tests**

Run: `make integration-sso && npm test`

Expected: all pass.

- [ ] **Step 7: Commit and push**

```bash
git add .env.example Makefile docker-compose.sso.yml platform/caddy platform/oauth2-proxy platform/site tests
git commit -m "Add the OIDC-protected admin scope"
git push origin HEAD
```

### Task 7: CI, dependency automation, and repository policy

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `.github/dependabot.yml`
- Create: `.github/branch-ruleset.json`
- Modify: `Makefile`

**Interfaces:**
- Required CI job names are stable: `lint`, `unit`, `build`, `integration`, `integration-sso`, and `ui`.
- The ruleset targets the default branch, requires those checks and one approving review, blocks force pushes/deletion, requires resolved conversations, and allows repository administrators to bypass.

- [ ] **Step 1: Add local CI aggregate commands**

Create deterministic `make check` coverage for Python/shell lint, configuration validation, unit tests, builds, base and SSO integration, and Playwright UI tests.

- [ ] **Step 2: Expand GitHub Actions**

Give the workflow `contents: read`, pin action major versions, use dependency caches, upload failure artifacts, and define the six stable job names. Ensure services and volumes are torn down under `if: always()`.

- [ ] **Step 3: Add Dependabot and declarative ruleset**

Configure monthly updates for GitHub Actions, Docker, npm, and Python. Store the exact GitHub ruleset payload in `.github/branch-ruleset.json` so remote policy remains reviewable.

- [ ] **Step 4: Run the complete local gate**

Run: `make check`

Expected: all checks pass.

- [ ] **Step 5: Commit and push**

```bash
git add .github Makefile
git commit -m "Expand CI and codify branch protection"
git push origin HEAD
```

- [ ] **Step 6: Apply and verify the GitHub ruleset**

Run `gh api --method POST repos/C-Nucifora/artifact-platform/rulesets --input .github/branch-ruleset.json`, or PATCH the matching ruleset when it already exists. Verify with `gh api repos/C-Nucifora/artifact-platform/rulesets` and confirm the six required check names and administrator bypass actor.

### Task 8: Deployment documentation and final verification

**Files:**
- Modify: `README.md`
- Create: `docs/authentik.md`
- Create: `docs/tailscale-ssh.md`
- Modify: `.env.example`

**Interfaces:**
- Documents exact base, Funnel, custom-domain SSO, Authentik, keyless SSH policy, config-file, UI-editing, troubleshooting, and rollback workflows.

- [ ] **Step 1: Rewrite deployment documentation**

Lead with local preview, then base Funnel deployment, the dedicated `artifact` SSH account and `accept` policy, mesh configuration examples, the SSO overlay command, Authentik OIDC registration/callback URL, secrets generation, admin group mapping, and verification commands.

- [ ] **Step 2: Run documentation and secret scans**

Run: `rg -n "TS_AUTHKEY=tskey|OIDC_CLIENT_SECRET=[^<]|COOKIE_SECRET=[^<]" . --glob '!docs/superpowers/**'` and `git diff --check`.

Expected: no committed secret values and no whitespace errors.

- [ ] **Step 3: Run final verification**

Run: `make check`

Expected: all local gates pass from a clean stack.

- [ ] **Step 4: Commit and push**

```bash
git add README.md docs .env.example
git commit -m "Document mesh and SSO deployment"
git push origin HEAD
```

- [ ] **Step 5: Verify GitHub state**

Use `gh run list --branch local-preview-no-tailnet-required --limit 5`, inspect the newest run to completion, verify the pull request is current, and confirm the default-branch ruleset remains active with administrator bypass.

