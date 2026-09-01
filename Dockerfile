FROM tailscale/tailscale:stable AS tailscale-cli

FROM python:3.14-alpine

RUN apk add --no-cache ca-certificates caddy tini \
    && addgroup -S -g 10001 artifact \
    && adduser -S -D -H -u 10001 -G artifact artifact

COPY --from=tailscale-cli /usr/local/bin/tailscale /usr/local/bin/tailscale

WORKDIR /app
COPY platform/discovery/discovery/ ./discovery/
COPY platform/site/ /srv/site/
COPY platform/caddy/Caddyfile.container /etc/caddy/Caddyfile
COPY platform/caddy/snippets/ /etc/caddy/snippets/
COPY scripts/start-container.sh /usr/local/bin/artifact-platform

RUN mkdir -p /artifacts /config /generated /tmp/caddy-data /tmp/caddy-config \
    && chmod 0755 /usr/local/bin/artifact-platform \
    && chown -R artifact:artifact \
        /artifacts /config /generated /tmp/caddy-data /tmp/caddy-config

ENV PYTHONUNBUFFERED=1 \
    DISCOVERY_ARTIFACTS_DIR=/artifacts \
    DISCOVERY_OUTPUT_DIR=/generated \
    MESH_CONFIG_PATH=/config/mesh.json \
    XDG_DATA_HOME=/tmp/caddy-data \
    XDG_CONFIG_HOME=/tmp/caddy-config

EXPOSE 8080

VOLUME ["/artifacts", "/config", "/generated"]

USER artifact:artifact

ENTRYPOINT ["/sbin/tini", "--", "/usr/local/bin/artifact-platform"]
