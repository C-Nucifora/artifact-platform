"""Validated, versioned operator configuration for the artifact mesh."""

import contextlib
import hashlib
import ipaddress
import json
import logging
import os
import re
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

log = logging.getLogger(__name__)

MAX_CONFIG_BYTES = 256 * 1024
MAX_PEERS = 500
MAX_EXCLUSIONS = 500
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
HOST_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")


class ConfigValidationError(ValueError):
    """The mesh configuration is malformed or contains unsafe values."""


class RevisionConflict(Exception):
    """The stored configuration changed after the caller read it."""


@dataclass(frozen=True)
class PeerRule:
    manual: bool = False
    ssh_target: str | None = None
    public_url: str | None = None
    excluded_artifacts: tuple[str, ...] = ()


@dataclass(frozen=True)
class MeshConfig:
    version: int = 1
    excluded_peers: tuple[str, ...] = ()
    peers: dict[str, PeerRule] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfigDocument:
    config: MeshConfig
    revision: str


def _require_keys(value: dict, allowed: set[str], label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        fields = ", ".join(sorted(unknown))
        raise ConfigValidationError(f"{label} contains unknown field(s): {fields}")


def _host(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 253:
        raise ConfigValidationError(f"{label} must be a hostname or Tailscale IP")
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    if not HOST_RE.fullmatch(value) or ".." in value:
        raise ConfigValidationError(f"{label} must be a hostname or Tailscale IP")
    invalid_label = any(
        not part or len(part) > 63 or part.startswith("-") or part.endswith("-")
        for part in value.split(".")
    )
    if invalid_label:
        raise ConfigValidationError(f"{label} must be a hostname or Tailscale IP")
    return value.lower()


def _https_url(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ConfigValidationError(f"{label} must be an HTTPS URL")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ConfigValidationError(
            f"{label} must be an HTTPS URL without credentials or query data"
        )
    path = parsed.path.rstrip("/")
    return urlunsplit(("https", parsed.netloc.lower(), path, "", ""))


def _slug_list(value: object, label: str, limit: int) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > limit:
        raise ConfigValidationError(f"{label} must be a list with at most {limit} entries")
    normalized = []
    for item in value:
        if not isinstance(item, str) or not SLUG_RE.fullmatch(item):
            raise ConfigValidationError(f"{label} contains an invalid slug")
        normalized.append(item)
    return tuple(sorted(set(normalized)))


def _peer_rule(raw: object, label: str) -> PeerRule:
    if not isinstance(raw, dict):
        raise ConfigValidationError(f"{label} must be an object")
    _require_keys(raw, {"manual", "ssh_target", "public_url", "excluded_artifacts"}, label)
    manual = raw.get("manual", False)
    if not isinstance(manual, bool):
        raise ConfigValidationError(f"{label}.manual must be true or false")
    rule = PeerRule(
        manual=manual,
        ssh_target=_host(raw["ssh_target"], f"{label}.ssh_target") if "ssh_target" in raw else None,
        public_url=(
            _https_url(raw["public_url"], f"{label}.public_url") if "public_url" in raw else None
        ),
        excluded_artifacts=_slug_list(
            raw.get("excluded_artifacts"), f"{label}.excluded_artifacts", MAX_EXCLUSIONS
        ),
    )
    if rule.manual and (rule.ssh_target is None or rule.public_url is None):
        raise ConfigValidationError(
            f"{label} requires ssh_target and public_url when manual is true"
        )
    return rule


def mesh_config_to_dict(config: MeshConfig) -> dict:
    """Return the normalized public representation used by file and API callers."""
    peers = {}
    for peer_id, rule in sorted(config.peers.items()):
        entry: dict[str, object] = {}
        if rule.manual:
            entry["manual"] = True
        if rule.ssh_target is not None:
            entry["ssh_target"] = rule.ssh_target
        if rule.public_url is not None:
            entry["public_url"] = rule.public_url
        if rule.excluded_artifacts:
            entry["excluded_artifacts"] = list(rule.excluded_artifacts)
        peers[peer_id] = entry
    return {
        "version": 1,
        "excluded_peers": list(config.excluded_peers),
        "peers": peers,
    }


def _document(config: MeshConfig) -> ConfigDocument:
    canonical = json.dumps(mesh_config_to_dict(config), sort_keys=True, separators=(",", ":"))
    return ConfigDocument(config=config, revision=hashlib.sha256(canonical.encode()).hexdigest())


def parse_mesh_config(raw: object) -> ConfigDocument:
    """Strictly validate and normalize an API-supplied config document."""
    if not isinstance(raw, dict):
        raise ConfigValidationError("configuration must be an object")
    _require_keys(raw, {"version", "excluded_peers", "peers"}, "configuration")
    if raw.get("version") != 1:
        raise ConfigValidationError("configuration version must be 1")

    excluded_raw = raw.get("excluded_peers", [])
    if not isinstance(excluded_raw, list) or len(excluded_raw) > MAX_PEERS:
        raise ConfigValidationError(
            f"excluded_peers must be a list with at most {MAX_PEERS} entries"
        )
    excluded = tuple(sorted({_host(item, "excluded_peers entry") for item in excluded_raw}))

    peers_raw = raw.get("peers", {})
    if not isinstance(peers_raw, dict) or len(peers_raw) > MAX_PEERS:
        raise ConfigValidationError(f"peers must be an object with at most {MAX_PEERS} entries")
    peers = {
        _host(peer_id, "peer identifier"): _peer_rule(rule, f"peers.{peer_id}")
        for peer_id, rule in peers_raw.items()
    }
    return _document(MeshConfig(excluded_peers=excluded, peers=peers))


def load_mesh_config(path: Path, fallback: ConfigDocument | None = None) -> ConfigDocument:
    """Load hand-edited config, retaining the last valid value after an edit error."""
    path = Path(path)
    try:
        if path.stat().st_size > MAX_CONFIG_BYTES:
            raise ConfigValidationError("configuration exceeds 256 KiB")
        raw = json.loads(path.read_text(encoding="utf-8"))
        return parse_mesh_config(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, ConfigValidationError) as exc:
        if not isinstance(exc, FileNotFoundError):
            log.warning("invalid mesh configuration at %s: %s", path, exc)
        return fallback or parse_mesh_config({"version": 1})


def save_mesh_config(
    path: Path, document: ConfigDocument, expected_revision: str | None
) -> ConfigDocument:
    """Atomically replace config unless the caller's revision is stale."""
    path = Path(path)
    if expected_revision is not None and path.exists():
        current = load_mesh_config(path)
        if current.revision != expected_revision:
            raise RevisionConflict("mesh configuration changed; reload before saving")

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(mesh_config_to_dict(document.config), indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        Path(tmp_name).replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            Path(tmp_name).unlink()
        raise
    return document


class ConfigStore:
    """Thread-safe config access that retains the last valid parsed document."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._document = load_mesh_config(self.path)

    def load(self) -> ConfigDocument:
        """Refresh from disk, falling back to the last valid in-memory value."""
        with self._lock:
            self._document = load_mesh_config(self.path, fallback=self._document)
            return self._document

    def save(self, document: ConfigDocument, expected_revision: str) -> ConfigDocument:
        """Serialize compare-and-replace so one revision cannot be spent twice."""
        with self._lock:
            current = self.load()
            if current.revision != expected_revision:
                raise RevisionConflict("mesh configuration changed; reload before saving")
            self._document = save_mesh_config(self.path, document, expected_revision=None)
            return self._document
