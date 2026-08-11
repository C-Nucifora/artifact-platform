FROM tailscale/tailscale:stable AS tailscale-cli

FROM python:3.13-alpine

RUN apk add --no-cache ca-certificates caddy tini

COPY --from=tailscale-cli /usr/local/bin/tailscale /usr/local/bin/tailscale

WORKDIR /app
COPY platform/discovery/discovery/ ./discovery/
COPY platform/site/ /srv/site/
COPY platform/caddy/Caddyfile.container /etc/caddy/Caddyfile
COPY platform/caddy/snippets/ /etc/caddy/snippets/
COPY scripts/start-container.sh /usr/local/bin/artifact-platform

RUN mkdir -p /artifacts /config /generated \
    && chmod 0755 /usr/local/bin/artifact-platform

ENV PYTHONUNBUFFERED=1 \
    DISCOVERY_ARTIFACTS_DIR=/artifacts \
    DISCOVERY_OUTPUT_DIR=/generated \
    MESH_CONFIG_PATH=/config/mesh.json

EXPOSE 8080

VOLUME ["/artifacts", "/config", "/generated"]

ENTRYPOINT ["/sbin/tini", "-g", "--", "/usr/local/bin/artifact-platform"]

