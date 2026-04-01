from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from promoai.general_utils.constants import temp_dir


ARTIFACTS_ROOT = Path(temp_dir) / "artifacts"
STAGING_ROOT = Path(temp_dir) / "_staging"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slugify(value: str, fallback: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return (sanitized or fallback)[:80]


def _normalize_for_manifest(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            str(key): _normalize_for_manifest(item)
            for key, item in list(value.items())[:20]
        }
    if isinstance(value, (list, tuple, set)):
        return [_normalize_for_manifest(item) for item in list(value)[:20]]
    return str(value)


def create_analysis_session(prefix: str = "pmax") -> str:
    session_name = (
        f"{_slugify(prefix, 'analysis')}_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_"
        f"{uuid4().hex[:8]}"
    )
    session_dir = _ensure_dir(ARTIFACTS_ROOT / session_name)
    return str(session_dir)


def get_session_subdir(session_dir: str, category: str) -> str:
    subdir = _ensure_dir(Path(session_dir) / _slugify(category, "artifacts"))
    return str(subdir)


def get_staging_dir(name: str) -> str:
    staging_dir = _ensure_dir(STAGING_ROOT / _slugify(name, "staging"))
    return str(staging_dir)


def create_managed_path(
    session_dir: str,
    category: str,
    description: str,
    suffix: str,
    prefix: str | None = None,
) -> str:
    target_dir = Path(get_session_subdir(session_dir, category))
    extension = suffix if suffix.startswith(".") else f".{suffix}"
    stem = _slugify(description, prefix or category)
    next_index = sum(1 for path in target_dir.iterdir() if path.is_file()) + 1
    return str(target_dir / f"{next_index:03d}_{stem}{extension}")


def write_text_artifact(
    session_dir: str,
    category: str,
    description: str,
    content: str,
    suffix: str = ".txt",
    prefix: str | None = None,
) -> str:
    artifact_path = Path(
        create_managed_path(session_dir, category, description, suffix, prefix=prefix)
    )
    artifact_path.write_text(content, encoding="utf-8")
    return str(artifact_path)


def write_json_artifact(
    session_dir: str,
    category: str,
    description: str,
    payload: Any,
    prefix: str | None = None,
) -> str:
    artifact_path = Path(
        create_managed_path(session_dir, category, description, ".json", prefix=prefix)
    )
    artifact_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(artifact_path)


def write_bytes_artifact(
    session_dir: str,
    category: str,
    filename: str,
    content: bytes,
    description: str | None = None,
    prefix: str | None = None,
) -> str:
    source_name = Path(filename)
    full_suffix = "".join(source_name.suffixes) or ".bin"
    artifact_path = Path(
        create_managed_path(
            session_dir,
            category,
            description or source_name.stem or category,
            full_suffix,
            prefix=prefix,
        )
    )
    artifact_path.write_bytes(content)
    return str(artifact_path)


def append_manifest_entry(
    session_dir: str,
    *,
    category: str,
    file_path: str,
    description: str,
    artifact_type: str | None = None,
    data_preview: Any = None,
    extra: dict[str, Any] | None = None,
) -> None:
    manifest_path = Path(session_dir) / "manifest.jsonl"
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "type": artifact_type or category,
        "file_path": str(Path(file_path)),
        "description": description,
    }
    if data_preview is not None:
        entry["data_preview"] = _normalize_for_manifest(data_preview)
    if extra:
        entry["extra"] = _normalize_for_manifest(extra)

    with manifest_path.open("a", encoding="utf-8") as manifest_file:
        manifest_file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def disk_cleanup(root: str, ttl: int = 3) -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=ttl)
    SESSION_RE = re.compile(r"^(?P<prefix>.+)_(?P<ts>\d{8}_\d{6})_(?P<id>[0-9a-f]{8})$")

    if not root.exists():
        return

    for path in root.iterdir():
        if not path.is_dir():
            continue

        m = SESSION_RE.match(path.name)
        if not m:
            continue

        try:
            ts = datetime.strptime(m.group("ts"), "%Y%m%d_%H%M%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue

        if ts < cutoff:
            shutil.rmtree(path, ignore_errors=True)
