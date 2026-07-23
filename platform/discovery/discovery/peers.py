"""Aggregate peer manifests into peers.json."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from discovery.tailnet import Device
from discovery.util import utc_now_iso

log = logging.getLogger(__name__)

MAX_WORKERS = 8


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
                "artifacts": manifest.get("artifacts") or [],
            }
            for device, manifest in results
        ],
        "generated_at": utc_now_iso(),
    }
