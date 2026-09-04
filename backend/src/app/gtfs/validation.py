from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings


@dataclass(frozen=True)
class ValidationResult:
    version: str
    report: dict[str, object]


def validate_feed(path: Path, settings: Settings) -> ValidationResult:
    jar = settings.gtfs_validator_jar
    if not jar.exists():
        raise FileNotFoundError(
            f"GTFS validator was requested but {jar} does not exist; use the gtfs-import container "
            "or pass --skip-validation for local development"
        )

    settings.gtfs_cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="validation-", dir=settings.gtfs_cache_dir) as output:
        result = subprocess.run(
            ["java", "-jar", str(jar), "-i", str(path), "-o", output],
            check=False,
            capture_output=True,
            text=True,
            timeout=30 * 60,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout)[-2000:]
            raise RuntimeError(f"GTFS validator failed: {detail}")

        output_path = Path(output)
        system_errors = _read_json(output_path / "system_errors.json", default=[])
        if _has_system_errors(system_errors):
            raise RuntimeError(f"GTFS validator reported system errors: {system_errors}")
        report = _read_json(output_path / "report.json", default={})
        if not isinstance(report, dict):
            raise TypeError("GTFS validator report.json had an unexpected format")
        return ValidationResult(version=settings.gtfs_validator_version, report=report)


def _read_json(path: Path, *, default: object) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _has_system_errors(value: object) -> bool:
    if isinstance(value, dict) and set(value) == {"notices"}:
        return bool(value["notices"])
    return bool(value)
