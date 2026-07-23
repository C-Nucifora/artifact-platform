# The tailscale CLI is copied from the same image family as the sidecar so the
# client and daemon stay version-aligned.
FROM tailscale/tailscale:stable AS tailscale-cli

FROM python:3.13-alpine

RUN apk add --no-cache ca-certificates

COPY --from=tailscale-cli /usr/local/bin/tailscale /usr/local/bin/tailscale

WORKDIR /app
COPY discovery/ ./discovery/

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "discovery"]
