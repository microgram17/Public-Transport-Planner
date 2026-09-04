from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import get_settings
from app.gtfs.download import download_feed, local_feed
from app.gtfs.loader import import_feed, was_imported
from app.gtfs.validation import validate_feed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download, validate, and import a GTFS Schedule feed")
    parser.add_argument("--file", type=Path, help="Use a local GTFS ZIP or extracted directory")
    parser.add_argument("--operator", help="Trafiklab operator abbreviation (default: GTFS_OPERATOR)")
    parser.add_argument("--skip-validation", action="store_true", help="Skip MobilityData validation")
    parser.add_argument("--force", action="store_true", help="Import even if this checksum already succeeded")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    operator = args.operator or settings.gtfs_operator
    if operator != settings.gtfs_operator:
        settings = settings.model_copy(update={"gtfs_operator": operator})

    try:
        feed = local_feed(args.file) if args.file else download_feed(settings)
        if not args.force and was_imported(settings.database_url, operator, feed.sha256):
            print(f"GTFS feed {feed.sha256[:12]} is already imported; nothing to do")
            return 0

        validation = None
        if settings.gtfs_validate and not args.skip_validation:
            print(f"Validating GTFS feed with MobilityData validator {settings.gtfs_validator_version}...")
            validation = validate_feed(feed.path, settings)

        print(f"Importing GTFS feed {feed.sha256[:12]} for {operator}...")
        result = import_feed(settings.database_url, operator, feed, validation)
    except Exception as exc:  # noqa: BLE001 - CLI boundary converts failures to a useful exit code.
        print(f"GTFS import failed: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "import_id": result.import_id,
                "feed_version": result.feed_version,
                "row_counts": result.row_counts,
                "ignored_columns": result.ignored_columns,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
