"""Retrieve peer manifests through identity-authenticated Tailscale SSH."""

import json
import logging
import os
import selectors
import subprocess
import time

from discovery.mesh import ResolvedPeer

log = logging.getLogger(__name__)

MAX_MANIFEST_BYTES = 1024 * 1024
MAX_STDERR_BYTES = 64 * 1024


class OutputLimitError(Exception):
    """The peer exceeded the maximum manifest response size."""


def _run_command_bounded(argv: list[str], timeout: float, max_stdout_bytes: int) -> str:
    """Run a process while enforcing byte and wall-clock limits during I/O."""
    process = subprocess.Popen(  # noqa: S603 - argv is a fixed, shell-free command
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    stdout = bytearray()
    stderr = bytearray()
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout, output=bytes(stdout))
            events = selector.select(remaining)
            if not events:
                raise subprocess.TimeoutExpired(argv, timeout, output=bytes(stdout))
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 64 * 1024)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stdout":
                    stdout.extend(chunk)
                    if len(stdout) > max_stdout_bytes:
                        raise OutputLimitError(f"stdout exceeded {max_stdout_bytes} bytes")
                elif len(stderr) < MAX_STDERR_BYTES:
                    stderr.extend(chunk[: MAX_STDERR_BYTES - len(stderr)])

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(argv, timeout, output=bytes(stdout))
        return_code = process.wait(timeout=remaining)
        if return_code:
            raise subprocess.CalledProcessError(
                return_code,
                argv,
                output=bytes(stdout),
                stderr=bytes(stderr),
            )
        return stdout.decode("utf-8")
    except BaseException:
        if process.poll() is None:
            process.kill()
        process.wait()
        raise
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()


def _run_ssh(argv: list[str], timeout: float) -> str:
    return _run_command_bounded(argv, timeout, MAX_MANIFEST_BYTES)


def fetch_manifest_ssh(
    peer: ResolvedPeer,
    socket_path: str,
    timeout: float,
    runner=_run_ssh,
) -> dict | None:
    """Return a peer manifest, or None when the bounded SSH read fails."""
    argv = [
        "tailscale",
        "--socket",
        socket_path,
        "ssh",
        f"artifact@{peer.ssh_target}",
        "cat",
        "/generated/manifest.json",
    ]
    try:
        raw = runner(argv, timeout)
    except (
        OSError,
        OutputLimitError,
        UnicodeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as exc:
        log.debug("%s: Tailscale SSH failed: %s", peer.peer_id, exc)
        return None
    if len(raw.encode("utf-8")) > MAX_MANIFEST_BYTES:
        log.debug("%s: manifest exceeded size limit", peer.peer_id)
        return None
    try:
        manifest = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError):
        log.debug("%s: manifest was not valid JSON", peer.peer_id)
        return None
    if not isinstance(manifest, dict) or not isinstance(manifest.get("artifacts"), list):
        log.debug("%s: manifest shape was invalid", peer.peer_id)
        return None
    return manifest
