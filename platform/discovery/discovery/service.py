"""Coordinate the discovery loop and internal management HTTP server."""

import logging
import signal
import threading

from discovery.api import create_server
from discovery.config import Config
from discovery.loop import run_once

log = logging.getLogger(__name__)


class DiscoveryController:
    def __init__(self, cfg: Config, runner=run_once):
        self._cfg = cfg
        self._runner = runner
        self._pending = threading.Event()
        self._stop = threading.Event()
        self._snapshot_lock = threading.Lock()
        self._discovered: list[dict] = []

    def trigger(self) -> bool:
        """Queue one pass, coalescing repeated requests while one is pending."""
        if self._pending.is_set():
            return False
        self._pending.set()
        return True

    def discovered_peers(self) -> list[dict]:
        with self._snapshot_lock:
            return [dict(peer) for peer in self._discovered]

    def run_pending_once(self) -> bool:
        if not self._pending.is_set():
            return False
        self._pending.clear()
        discovered = self._runner(self._cfg)
        with self._snapshot_lock:
            self._discovered = [dict(peer) for peer in discovered]
        return True

    def stop(self) -> None:
        self._stop.set()
        self._pending.set()

    def run_forever(self) -> None:
        self.trigger()
        while not self._stop.is_set():
            try:
                self.run_pending_once()
            except Exception:
                log.exception("discovery cycle failed; will retry next interval")
            self._pending.wait(self._cfg.interval)
            self._pending.set()


def run_service(cfg: Config) -> None:
    """Run discovery in the main thread and management HTTP in a worker."""
    controller = DiscoveryController(cfg)
    server = create_server(cfg, controller)
    api_thread = threading.Thread(target=server.serve_forever, name="management-api", daemon=True)

    def handle_signal(signum, frame):
        log.info("received signal %d, shutting down", signum)
        controller.stop()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    api_thread.start()
    log.info("management API listening on %s:%d", cfg.management_host, cfg.management_port)
    try:
        controller.run_forever()
    finally:
        server.shutdown()
        server.server_close()
        api_thread.join(timeout=5)
