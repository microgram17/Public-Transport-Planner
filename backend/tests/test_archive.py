from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.gtfs.archive import FeedArchive, sha256_path


def test_reads_nested_zip_and_utf8_bom(tmp_path: Path) -> None:
    archive_path = tmp_path / "feed.zip"
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("nested/stops.txt", "\ufeffstop_id,stop_name\n1,Årstaberg\n")

    with FeedArchive(archive_path) as archive:
        assert archive.has("stops.txt")
        assert archive.header("stops.txt") == ["stop_id", "stop_name"]
        assert b"rstaberg" in b"".join(archive.chunks("stops.txt"))

    assert len(sha256_path(archive_path)) == 64


def test_rejects_duplicate_basenames(tmp_path: Path) -> None:
    archive_path = tmp_path / "feed.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("one/stops.txt", "stop_id\n1\n")
        archive.writestr("two/stops.txt", "stop_id\n2\n")

    with pytest.raises(ValueError, match="more than one stops.txt"), FeedArchive(archive_path):
        pass


def test_directory_hash_is_stable(tmp_path: Path) -> None:
    (tmp_path / "routes.txt").write_text("route_id\n1\n", encoding="utf-8")
    first = sha256_path(tmp_path)
    second = sha256_path(tmp_path)
    assert first == second
