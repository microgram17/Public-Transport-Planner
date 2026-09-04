from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.config import Settings
from app.gtfs.archive import sha256_path


@dataclass(frozen=True)
class DownloadedFeed:
    path: Path
    sha256: str
    etag: str | None
    downloaded_at: datetime
    source: str
    not_modified: bool = False


def local_feed(path: Path) -> DownloadedFeed:
    resolved = path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"GTFS input does not exist: {resolved}")
    return DownloadedFeed(
        path=resolved,
        sha256=sha256_path(resolved),
        etag=None,
        downloaded_at=datetime.now(UTC),
        source=str(resolved),
    )


def download_feed(settings: Settings) -> DownloadedFeed:
    api_key = settings.gtfs_regional_static_api_key_value
    if api_key is None:
        raise ValueError("GTFS_REGIONAL_STATIC_API_KEY must be set when downloading a feed")

    cache_dir = settings.gtfs_cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    archive_path = cache_dir / f"{settings.gtfs_operator}.zip"
    state_path = cache_dir / f"{settings.gtfs_operator}.http.json"
    state = _read_state(state_path)
    headers: dict[str, str] = {}
    if state.get("etag"):
        headers["If-None-Match"] = state["etag"]
    if state.get("last_modified"):
        headers["If-Modified-Since"] = state["last_modified"]

    try:
        with (
            httpx.Client(follow_redirects=True, timeout=120) as client,
            client.stream(
                "GET",
                settings.trafiklab_download_url,
                params={"key": api_key},
                headers=headers,
            ) as response,
        ):
            if response.status_code == 304:
                if not archive_path.exists():
                    raise RuntimeError("Trafiklab returned 304 but the cached archive is missing")
                return DownloadedFeed(
                    path=archive_path,
                    sha256=sha256_path(archive_path),
                    etag=state.get("etag"),
                    downloaded_at=datetime.now(UTC),
                    source=settings.trafiklab_download_url,
                    not_modified=True,
                )
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(dir=cache_dir, suffix=".zip", delete=False) as temporary:
                temporary_path = Path(temporary.name)
                for chunk in response.iter_bytes(1024 * 1024):
                    temporary.write(chunk)
            os.replace(temporary_path, archive_path)
            etag = response.headers.get("etag")
            _write_state(
                state_path,
                {"etag": etag, "last_modified": response.headers.get("last-modified")},
            )
    except httpx.HTTPError as exc:
        raise RuntimeError("Unable to download the Trafiklab GTFS archive") from exc

    return DownloadedFeed(
        path=archive_path,
        sha256=sha256_path(archive_path),
        etag=etag,
        downloaded_at=datetime.now(UTC),
        source=settings.trafiklab_download_url,
    )


def _read_state(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_state(path: Path, value: dict[str, str | None]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value), encoding="utf-8")
    os.replace(temporary, path)
