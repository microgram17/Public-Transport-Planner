from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Iterator
from pathlib import Path
from typing import Self
from zipfile import ZipFile


class FeedArchive:
    """Read GTFS members from either a ZIP archive or an extracted directory."""

    def __init__(self, path: Path):
        self.path = path
        self._zip: ZipFile | None = None
        self._members: dict[str, str | Path] = {}

    def __enter__(self) -> Self:
        if self.path.is_dir():
            candidates: list[str | Path] = sorted(self.path.rglob("*.txt"))
        else:
            self._zip = ZipFile(self.path)
            candidates = [name for name in self._zip.namelist() if name.lower().endswith(".txt")]

        for candidate in candidates:
            name = Path(candidate).name.lower()
            if name in self._members:
                raise ValueError(f"GTFS input contains more than one {name}")
            self._members[name] = candidate
        return self

    def __exit__(self, *_: object) -> None:
        if self._zip is not None:
            self._zip.close()

    def has(self, filename: str) -> bool:
        return filename.lower() in self._members

    def header(self, filename: str) -> list[str]:
        with self._open(filename) as binary, io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
            try:
                return next(csv.reader(text))
            except StopIteration as exc:
                raise ValueError(f"{filename} is empty") from exc

    def chunks(self, filename: str, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        with self._open(filename) as stream:
            while chunk := stream.read(chunk_size):
                yield chunk

    def _open(self, filename: str):
        member = self._members.get(filename.lower())
        if member is None:
            raise FileNotFoundError(filename)
        if self._zip is not None:
            return self._zip.open(str(member), "r")
        return Path(member).open("rb")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    files = sorted(path.rglob("*.txt"))
    for file in files:
        digest.update(file.relative_to(path).as_posix().encode())
        with file.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    return digest.hexdigest()
