# Product

<!-- impeccable:product-schema 1 -->

> Product facts below are inferred from the repository and the user's explicit brief. The user asked implementation to continue without further interview prompts.

## Platform

web

## Users

Operators host and share small web artifacts across multiple personal or team devices. Visitors browse and launch those artifacts from a unified catalog. Authenticated administrators manage which nodes and endpoints participate in the mesh.

## Product Purpose

Artifact Platform makes independently hosted artifact collections behave like one discoverable mesh. Success means a node can join with minimal setup, find eligible peers automatically, exchange trusted metadata privately, and send visitors to working public artifact endpoints.

## Positioning

Each node remains self-contained while Tailscale identity supplies the mesh control plane and public HTTPS endpoints supply artifact delivery. There is no central peer registry and no user-managed SSH key distribution.

## Operating Context

The platform runs as a Docker Compose stack on multiple tailnet devices. Operators work with Tailscale enrollment and policy, Funnel or custom-domain HTTPS, JSON configuration, Authentik-compatible OIDC, and static artifact folders containing optional metadata.

## Capabilities and Constraints

- All eligible discovered peers mesh by default.
- Operators can exclude peers or artifacts, add manual peers, and override SSH or public endpoints through file or authenticated UI.
- Peer manifests travel through Tailscale SSH using a dedicated unprivileged account.
- Artifact resources are served through Funnel or a configured HTTPS site endpoint.
- The anonymous catalog remains useful without SSO.
- Admin routes exist only in the SSO-enabled deployment.
- The frontend uses static HTML, CSS, and JavaScript without a client framework.

## Brand Commitments

The product name is Artifact Platform. The requested interface combines an infrastructure control plane with a polished artifact gallery, leaning technical and operational rather than editorial.

## Evidence on Hand

The repository contains real manifest and peer fixtures, integration tests, artifact templates, runtime configuration, and architecture documentation. It contains no customer claims, benchmarks, testimonials, or approved logo assets; future work must not invent them.

## Product Principles

- Default to a useful automatic mesh, then make exceptions explicit.
- Keep identity-backed control traffic private and artifact delivery simple.
- Reveal operational state without exposing internal secrets or raw errors.
- Preserve local ownership and graceful partial failure.
- Make privileged capability structurally absent when authentication is disabled.

## Accessibility & Inclusion

The web interface must support keyboard navigation, visible focus, reduced motion, responsive layouts, semantic structure, and WCAG AA contrast.
