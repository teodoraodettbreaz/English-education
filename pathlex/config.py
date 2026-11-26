from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    host: str
    port: int
    database_path: Path
    static_path: Path
    max_request_bytes: int
    max_paths: int
    max_nodes: int

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("PATHLEX_DATA_DIR", str(Path.cwd() / "data"))).expanduser()
        database_path = Path(
            os.getenv("PATHLEX_DATABASE_PATH", str(data_dir / "pathlex.sqlite3"))
        ).expanduser()
        return cls(
            host=os.getenv("PATHLEX_HOST", "127.0.0.1"),
            port=_positive_int("PATHLEX_PORT", 8080),
            database_path=database_path,
            static_path=PROJECT_ROOT / "pathlex" / "static",
            max_request_bytes=_positive_int("PATHLEX_MAX_REQUEST_BYTES", 1_000_000),
            max_paths=_positive_int("PATHLEX_MAX_PATHS", 64),
            max_nodes=_positive_int("PATHLEX_MAX_NODES", 255),
        )

