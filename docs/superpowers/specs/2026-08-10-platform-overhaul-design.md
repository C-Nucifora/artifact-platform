# Artifact Platform Overhaul Design

## Goal

Turn the existing static artifact index into a polished technical control plane. Every online platform node should mesh automatically, exchange its manifest over Tailscale SSH without user-managed SSH keys, and link visitors to artifacts through the node's public HTTPS endpoint. Operators can exclude, add, or override peers through either a local config file or an SSO-protected admin interface.

## Product surfaces

### Public catalog

The anonymous site remains useful without SSO. It shows the local node, mesh status, artifacts on this node, and artifacts discovered on other nodes. Artifact links always use a validated public HTTPS base URL. The presentation is a dark, infrastructure-oriented dashboard with a polished gallery hierarchy rather than a generic card list.

### Admin control plane

The admin interface appears only in the SSO deployment. It supports:

- excluding or restoring an automatically discovered peer;
- adding and removing manual peers;
- overriding a peer's SSH target or public URL;
- excluding individual artifact endpoints by peer and slug;
- seeing whether a value is discovered, overridden, manual, or excluded; and
- saving changes with clear validation and failure feedback.

The public deployment does not route the admin page, admin API, or OAuth callback paths. Hiding controls in the browser is not considered authorization.

## Architecture

### Tailscale sidecar

The Tailscale node continues to own tailnet and Funnel connectivity. Tailscale SSH is enabled on the node. A custom sidecar image defines a dedicated, unprivileged `artifact` operating-system user and mounts generated manifests read-only. The intended SSH policy allows non-interactive access to that user from eligible mesh nodes. It must not grant peer nodes a root login.

Tailscale authenticates and authorizes SSH using tailnet node identity, so operators do not create or distribute SSH keys. Each device still requires one-time tailnet enrollment, and the tailnet administrator must install an `accept` SSH rule. A `check` rule is not suitable for the automated discovery loop because it may require interactive reauthentication.

### Discovery and management service

The existing Python discovery process becomes a small standard-library HTTP service as well as a background loop. It:

1. builds the local manifest;
2. obtains online nodes from `tailscale status --json`;
3. merges discovered nodes with the operator configuration;
4. omits excluded peers before connection attempts;
5. retrieves each remaining manifest with a bounded `tailscale ssh artifact@<target> cat /generated/manifest.json` command;
6. validates and sanitizes peer data;
7. writes `manifest.json`, `peers.json`, and discovery status atomically; and
8. exposes a loopback/internal management API for reading and replacing configuration.

The service never listens directly on a host or public interface. Caddy is its only HTTP caller.

### Caddy and authentication

Caddy serves the catalog, artifacts, and generated JSON. Two deployment modes are supported:

- Base mode preserves local preview and Funnel delivery and has no admin routes.
- SSO mode is enabled with a Compose overlay. It adds OAuth2 Proxy, mounts an SSO-specific Caddy configuration, and exposes the platform on an operator-provided HTTPS site endpoint. `/admin`, `/api/admin/*`, and OAuth callback traffic pass through OAuth2 Proxy. Public catalog and artifact routes remain anonymous.

OAuth2 Proxy uses generic OIDC discovery and is documented for Authentik. The deployment administrator supplies the issuer URL, client ID, client secret, cookie secret, and allowed admin group. End users authenticate in the browser and manage no keys.

## Configuration model

The source of truth is a JSON file stored under `config/mesh.json`. A bind-mounted default file makes hand editing straightforward; the management service writes updates atomically. The schema is versioned:

```json
{
  "version": 1,
  "excluded_peers": ["retired-node.tailnet.ts.net"],
  "peers": {
    "studio.tailnet.ts.net": {
      "ssh_target": "studio.tailnet.ts.net",
      "public_url": "https://artifacts.example.com",
      "excluded_artifacts": ["private-demo"]
    },
    "manual-node": {
      "manual": true,
      "ssh_target": "manual-node.tailnet.ts.net",
      "public_url": "https://manual.example.com",
      "excluded_artifacts": []
    }
  }
}
```

Unknown fields are rejected by the admin API and ignored with a warning during file loading so a hand-edited mistake does not stop discovery. Peer identifiers, SSH targets, HTTPS URLs, and slugs receive strict length and character validation. The API uses whole-document replacement with an `If-Match` revision to prevent silent last-writer-wins updates.

Discovery defaults to a full mesh. A discovered node is included unless its canonical MagicDNS name is excluded. An override augments the discovered record. A manual record participates even when absent from `tailscale status`. Excluded artifacts are removed before `peers.json` is published.

## Public data contracts

`manifest.json` retains version 1 compatibility and adds optional public URL and health metadata. `peers.json` advances to version 2 and contains only safe, presentation-ready data:

- canonical identity and display hostname;
- validated public URL;
- connection state (`online`, `manual`, `unreachable`);
- source (`discovered`, `overridden`, `manual`);
- last successful synchronization timestamp; and
- sanitized artifact entries.

SSH targets, exclusion rules, raw errors, and SSO identity data are never published in these documents.

## Admin API

The internal API contains three endpoints:

- `GET /api/admin/config` returns the normalized configuration, its revision, and discovered peer summaries.
- `PUT /api/admin/config` validates and atomically replaces the document when `If-Match` matches.
- `POST /api/admin/discover` triggers an immediate bounded discovery pass and returns accepted/rejected status.

Requests must arrive through the authenticated Caddy route. The service also requires a shared internal bearer secret injected into Caddy and the service, preventing direct container-network callers from impersonating the proxy. OAuth2 Proxy supplies the verified user and group headers for audit logging; client-supplied versions are stripped.

## Visual system

The interface combines a technical control plane with an artifact gallery:

- near-black navy surfaces with cool slate borders and a restrained electric-cyan signal color;
- a compact monospace eyebrow and operational metadata paired with a readable sans-serif body face;
- a top status rail for node identity, mesh reachability, synchronization time, and artifact count;
- responsive artifact cards with strong titles, descriptions, peer provenance, and directional launch affordances;
- peer groups that read as connected nodes rather than repeated generic sections;
- deliberate empty, loading, partial-failure, and offline states;
- keyboard-visible focus, semantic landmarks, reduced-motion support, and AA-level contrast; and
- responsive behavior from a single mobile column to a wide control-plane grid.

The admin view reuses the same shell and adds a peer table/editor. Destructive exclusions require explicit confirmation and remain reversible. Form state clearly distinguishes saved configuration from unsaved edits.

No frontend framework is introduced. The current single static page is split into focused HTML, CSS, and JavaScript assets. The small surface does not justify a bundler or client framework.

## Failure behavior

Failure of Tailscale status, one SSH connection, malformed peer output, or a hand-edited config does not stop the service. The last valid generated documents remain available until a replacement can be written. Per-peer SSH commands have a hard timeout and the batch has a wall-clock deadline. Failures are logged with peer identity but without secrets, and the public UI reports degraded synchronization without exposing internal error strings.

An unavailable OIDC provider affects only authenticated routes. Public catalog and artifacts continue to work. Invalid SSO configuration fails the SSO overlay health check instead of exposing unprotected admin routes.

## Testing and verification

Unit tests cover SSH command construction and parsing, timeout/failure handling, configuration validation and merging, exclusions, overrides, manual peers, revisions, and API authorization. Integration tests cover the public Caddy surface, absence of admin routes in base mode, protected routing in SSO mode with a stub auth upstream, static assets, security headers, and existing artifact behavior.

Manual verification covers responsive layouts, keyboard navigation, reduced motion, empty and populated data, OAuth login with Authentik, automatic SSH meshing between two enrolled nodes, config edits from both file and UI, and Funnel/custom-domain artifact links.

CI runs formatting and lint checks, Python unit tests, configuration validation, container builds, HTTP integration tests, and browser-level UI checks. GitHub dependency update configuration and workflow permissions use least privilege. The repository's default branch is protected through a GitHub ruleset that requires a pull request, resolved conversations, and the named CI checks. Force pushes and branch deletion are blocked for normal contributors. Repository administrators are configured as ruleset bypass actors so emergency changes remain possible and auditable.

## Documentation and migration

The README will lead with a local preview path, then describe base Funnel deployment, keyless Tailscale SSH meshing, the required tailnet SSH policy, custom-domain SSO deployment, Authentik setup, and config examples. Existing artifact folders and metadata remain compatible. Existing HTTP manifest fetching is removed after the SSH path is covered by tests.
