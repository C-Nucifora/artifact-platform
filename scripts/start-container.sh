#!/bin/sh
set -eu

python -m discovery &
discovery_pid=$!

caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
caddy_pid=$!

shutdown() {
    trap - TERM INT
    kill -TERM "$discovery_pid" "$caddy_pid" 2>/dev/null || true
    wait "$discovery_pid" "$caddy_pid" 2>/dev/null || true
}

trap shutdown TERM INT

while kill -0 "$discovery_pid" 2>/dev/null && kill -0 "$caddy_pid" 2>/dev/null; do
    sleep 1
done

shutdown
exit 1
