"""Environment-driven configuration."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_ARTIFACTS_DIR = "/artifacts"
DEFAULT_OUTPUT_DIR = "/data"
DEFAULT_INTERVAL = 120.0
DEFAULT_FETCH_TIMEOUT = 5.0
DEFAULT_SOCKET = "/var/run/tailscale/tailscaled.sock"
DEFAULT_MESH_CONFIG = "/config/mesh.json"
DEFAULT_MANAGEMENT_HOST = "0.0.0.0"  # noqa: S104 - container network only; never host-published
DEFAULT_MANAGEMENT_PORT = 8090


def _positive_float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = -1.0
    if value <= 0:
        log.warning("%s=%r is not a positive number; using default %s", key, raw, default)
        return default
    return value


@dataclass(frozen=True)
class Config:
    artifacts_dir: Path
    output_dir: Path
    interval: float
    fetch_timeout: float
    socket_path: str
    mesh_config_path: Path = Path(DEFAULT_MESH_CONFIG)
    management_api_token: str = ""
    management_host: str = DEFAULT_MANAGEMENT_HOST
    management_port: int = DEFAULT_MANAGEMENT_PORT

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Config":
        return cls(
            artifacts_dir=Path(env.get("DISCOVERY_ARTIFACTS_DIR", DEFAULT_ARTIFACTS_DIR)),
            output_dir=Path(env.get("DISCOVERY_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)),
            interval=_positive_float(env, "DISCOVERY_INTERVAL", DEFAULT_INTERVAL),
            fetch_timeout=_positive_float(env, "DISCOVERY_FETCH_TIMEOUT", DEFAULT_FETCH_TIMEOUT),
            socket_path=env.get("TS_SOCKET", DEFAULT_SOCKET),
            mesh_config_path=Path(env.get("MESH_CONFIG_PATH", DEFAULT_MESH_CONFIG)),
            management_api_token=env.get("MANAGEMENT_API_TOKEN", ""),
            management_host=env.get("MANAGEMENT_HOST", DEFAULT_MANAGEMENT_HOST),
            management_port=int(env.get("MANAGEMENT_PORT", DEFAULT_MANAGEMENT_PORT)),
        )
