FROM tailscale/tailscale:stable

# Tailscale SSH maps the policy-approved remote login to this deliberately
# unprivileged account. It can read the generated manifest mount and nothing
# in the persistent Tailscale state volume.
RUN addgroup -S artifact \
    && adduser -S -D -H -s /bin/sh -G artifact artifact
