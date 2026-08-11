#!/bin/sh
set -eu

python -m discovery &
discovery_pid=$!

caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
caddy_pid=$!

shutdown() {
    kill -TERM "$discovery_pid" "$caddy_pid" 2>/dev/null || true
    wait "$discovery_pid" "$caddy_pid" 2>/dev/null || true
}

trap 'trap - TERM INT; shutdown; exit 0' TERM INT

while kill -0 "$discovery_pid" 2>/dev/null && kill -0 "$caddy_pid" 2>/dev/null; do
    sleep 1
done

shutdown
exit 1
