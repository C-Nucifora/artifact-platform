# Authentik OIDC setup

The SSO overlay publishes the catalog on a custom hostname while keeping the
catalog anonymous and placing the admin HTML, JavaScript, and management API
behind Authentik-compatible OIDC. OAuth2 Proxy performs login and group
authorization; Caddy enforces it before serving or proxying any admin route.

## Create the Authentik provider

In Authentik:

1. Create an OAuth2/OpenID Provider with a confidential client.
2. Set the strict redirect URI to
   `https://artifacts.example.com/oauth2/callback`, replacing the hostname.
3. Include the standard `openid`, `profile`, and `email` scopes. Authentik's
   profile mapping must include group membership as the `groups` claim.
4. Create an application using that provider.
5. Add administrators to `artifact-platform-admins`, or choose another group
   and set `OIDC_ADMIN_GROUP` to its exact name.

Copy the provider's client ID, client secret, and issuer URL. An Authentik
issuer commonly has this shape:

```text
https://auth.example.com/application/o/artifact-platform/
```

Use the issuer shown by Authentik rather than constructing it by hand.

## Configure the deployment

Create `.env`:

```dotenv
TS_HOSTNAME=artifacts
TS_AUTHKEY=
MANAGEMENT_API_TOKEN=<output of openssl rand -hex 32>
SITE_ADDRESS=artifacts.example.com
OIDC_ISSUER_URL=https://auth.example.com/application/o/artifact-platform/
OIDC_CLIENT_ID=<provider client id>
OIDC_CLIENT_SECRET=<provider client secret>
OIDC_COOKIE_SECRET=<output of openssl rand -base64 32>
OIDC_ADMIN_GROUP=artifact-platform-admins
```

Point the custom hostname at this host and allow inbound TCP 80/443. Start the
base stack plus the SSO overlay:

```sh
docker compose -f docker-compose.yml -f docker-compose.sso.yml config -q
docker compose -f docker-compose.yml -f docker-compose.sso.yml up -d
```

Caddy obtains the site's TLS certificate. OAuth2 Proxy listens only inside the
shared network namespace; it is not published directly.

## Security boundary

Public routes remain available without login:

- `/`
- `/styles.css`, `/app.js`, and fonts
- `/manifest.json` and `/peers.json`
- `/artifacts/*`

Authentication and the allowed group are required for:

- `/admin`, `/admin/`, `/admin.html`, and `/admin.js`
- `/api/admin/*`

Caddy removes client-supplied identity headers before forward-auth. On a valid
session it injects `MANAGEMENT_API_TOKEN` only into the upstream management
request. The browser never receives or stores that bearer token. Configuration
writes use revision/ETag matching so concurrent edits fail instead of silently
overwriting one another.

## Verify

```sh
curl -I https://artifacts.example.com/
curl -I https://artifacts.example.com/admin
docker compose -f docker-compose.yml -f docker-compose.sso.yml logs oauth2-proxy caddy
```

The catalog should return success without authentication. The admin request
should redirect to login, then return the admin console only for a member of
the configured group. A logged-in user without the group should receive 403.

If login loops, compare the scheme, hostname, path, and trailing slash of the
configured issuer and callback with Authentik exactly. If every user receives
403, inspect the ID token claims and confirm `groups` contains the configured
group name.
