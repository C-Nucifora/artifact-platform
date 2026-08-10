"""Small shared helpers."""

import contextlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def write_json_atomic(path: Path, obj: object) -> None:
    """Write JSON to `path` via a temp file + rename so readers never see a partial file."""
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=False)
            f.write("\n")
            os.fchmod(f.fileno(), 0o644)
        Path(tmp_name).replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            Path(tmp_name).unlink()
        raise
