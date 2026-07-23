"""Aggregate peer manifests into peers.json."""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from discovery.tailnet import Device
from discovery.util import utc_now_iso

log = logging.getLogger(__name__)

MAX_WORKERS = 8
MAX_ARTIFACTS_PER_PEER = 200
MAX_TEXT_CHARS = 300
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _sanitize_artifacts(raw: object) -> list[dict]:
    """Reduce a peer's artifact list to entries we're willing to render.

    A peer controls everything in its own manifest, and our index page turns
    these into links on a publicly reachable site. So the slug must look like a
    slug, text is truncated, and `path` is rebuilt here rather than trusted —
    a peer-supplied path like "@evil.example" would otherwise concatenate into
    a URL pointing at someone else's host.
    """
    if not isinstance(raw, list):
        return []
    entries = []
    for entry in raw[:MAX_ARTIFACTS_PER_PEER]:
        if not isinstance(entry, dict):
            continue
        slug = entry.get("slug")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            continue
        title = entry.get("title")
        description = entry.get("description")
        entries.append(
            {
                "slug": slug,
                "title": (title if isinstance(title, str) else slug)[:MAX_TEXT_CHARS],
                "description": (description if isinstance(description, str) else "")[
                    :MAX_TEXT_CHARS
                ],
                "path": f"/artifacts/{slug}/",
            }
        )
    return entries


def build_peers(
    devices: list[Device],
    fetcher,
    timeout: float,
    deadline: float | None = None,
) -> dict:
    """Fetch each peer's manifest concurrently and keep the ones that respond.

    `fetcher(device, timeout)` returns a manifest dict or None. Fetches that
    fail, raise, or outlive `deadline` (a wall-clock cap for the whole batch,
    default timeout + 5s) are skipped — this function never raises and never
    hangs on a stuck peer.
    """
    if deadline is None:
        deadline = timeout + 5.0

    results: list[tuple[Device, dict]] = []
    if devices:
        executor = ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(devices)))
        try:
            futures = {executor.submit(fetcher, device, timeout): device for device in devices}
            try:
                for future in as_completed(futures, timeout=deadline):
                    device = futures[future]
                    try:
                        manifest = future.result()
                    except Exception as exc:
                        log.debug("%s: fetcher raised: %s", device.dns_name, exc)
                        continue
                    if manifest is not None:
                        results.append((device, manifest))
            except TimeoutError:
                pending = [d.dns_name for f, d in futures.items() if not f.done()]
                log.debug("peer fetch deadline hit; skipping: %s", ", ".join(pending))
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    results.sort(key=lambda pair: pair[0].dns_name)
    return {
        "version": 1,
        "peers": [
            {
                "hostname": device.hostname,
                "dns_name": device.dns_name,
                "url": f"https://{device.dns_name}",
                "artifacts": _sanitize_artifacts(manifest.get("artifacts")),
            }
            for device, manifest in results
        ],
        "generated_at": utc_now_iso(),
    }
