# Tailscale SSH mesh setup

Artifact Platform uses Tailscale SSH as a machine-to-machine identity layer.
It does not generate an OpenSSH keypair, mount private keys, or manage
`authorized_keys`. Tailscale authenticates the source node and destination
node using their existing tailnet identities.

## One-time tailnet policy

Merge `platform/tailscale/policy.example.hujson` into the tailnet policy. Its
four pieces have distinct jobs:

- `tagOwners` allows administrators to enroll platform nodes with
  `tag:artifact-platform`;
- `grants` permits TCP 22 only between those tagged nodes;
- `ssh` automatically accepts the unprivileged `artifact` account between
  those nodes, avoiding an interactive approval during discovery;
- `nodeAttrs` permits Funnel for those nodes.

Do not change the SSH action to `check`: automated discovery cannot complete
an interactive check-mode approval. Restricting both source and destination to
the platform tag prevents unrelated tailnet devices from using this rule.

The image creates the `artifact` account with no home directory. It can read
the generated, read-only manifest and is not used to run arbitrary discovery
commands; the client invokes only:

```text
cat /generated/manifest.json
```

## Enroll each node

Leave `TS_AUTHKEY` empty and choose a unique hostname:

```sh
cp .env.example .env
# edit TS_HOSTNAME
docker compose up -d
docker compose logs tailscale
```

Open the printed Tailscale login URL as an administrator allowed by
`tagOwners`. Compose passes `--ssh --advertise-tags=tag:artifact-platform`
automatically. The login is a one-time node enrollment, not an SSH credential.

For fully unattended infrastructure, `TS_AUTHKEY` remains supported, but it is
not required for normal setup.

## Verify identity and discovery

```sh
docker compose exec tailscale tailscale status
docker compose exec tailscale tailscale ssh artifact@<peer-magicdns-name> \
  cat /generated/manifest.json
docker compose logs discovery
```

The second command should return JSON without an SSH host-key prompt, private
key option, or password. Within one `DISCOVERY_INTERVAL`, `/peers.json` should
show the peer with `transport` set to `tailscale-ssh` and a sanitized public
artifact URL.

## Funnel publishing

Enable MagicDNS and HTTPS certificates for the tailnet. The included serve
configuration terminates HTTPS on port 443, proxies Caddy on `127.0.0.1:80`,
and requests Funnel for that same endpoint.

```sh
docker compose exec tailscale tailscale funnel status
curl https://<hostname>.<tailnet>.ts.net/manifest.json
```

Funnel serves artifacts and the public catalog. It never exposes the admin
scope; the base Caddy policy returns 404 for all admin and OAuth routes.

## Removing or recovering a node

Use the Tailscale admin console to expire or delete a device. Locally,
`docker compose down -v` removes its persistent Tailscale identity and all
other named volumes; this is destructive and the next start requires a fresh
browser enrollment.
