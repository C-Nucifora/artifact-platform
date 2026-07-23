"""Build this device's manifest.json from the artifacts/ tree."""

import json
import logging
from pathlib import Path

from discovery.util import utc_now_iso

log = logging.getLogger(__name__)


def _read_meta(artifact_dir: Path) -> dict:
    meta_path = artifact_dir / "meta.json"
    try:
        raw = meta_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        meta = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        log.debug("ignoring malformed meta.json in %s", artifact_dir)
        return {}
    return meta if isinstance(meta, dict) else {}


def _str_or(value: object, fallback: str) -> str:
    return value if isinstance(value, str) else fallback


def build_manifest(artifacts_dir: Path, device: dict | None = None) -> dict:
    """Scan artifacts_dir and return the manifest document.

    Every non-hidden directory is an artifact. meta.json is optional; the slug
    stands in for a missing or malformed title, and description defaults to "".
    """
    artifacts_dir = Path(artifacts_dir)
    entries = []
    try:
        children = sorted(artifacts_dir.iterdir())
    except OSError:
        children = []
    for child in children:
        if not child.is_dir() or child.name.startswith("."):
            continue
        slug = child.name
        meta = _read_meta(child)
        entries.append(
            {
                "slug": slug,
                "title": _str_or(meta.get("title"), slug),
                "description": _str_or(meta.get("description"), ""),
                "path": f"/artifacts/{slug}/",
            }
        )
    return {
        "version": 1,
        "device": device or {},
        "artifacts": entries,
        "generated_at": utc_now_iso(),
    }
