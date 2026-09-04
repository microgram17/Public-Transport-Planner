from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from app.gtfs.archive import FeedArchive
from app.gtfs.download import DownloadedFeed
from app.gtfs.manifest import PROMOTION_ORDER, TABLE_BY_NAME, TABLES, Field, Table
from app.gtfs.validation import ValidationResult

ADVISORY_LOCK_NAMESPACE = 947_311
VALID_HEADER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PG_TYPES = {
    "text": "text",
    "integer": "integer",
    "smallint": "smallint",
    "double": "double precision",
    "boolean": "boolean",
    "date": "date",
    "gtfs_time": "integer",
}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImportResult:
    import_id: int
    feed_version: str | None
    row_counts: dict[str, int]
    ignored_columns: dict[str, list[str]]


def was_imported(database_url: str, operator: str, sha256: str) -> bool:
    """Return true only when this feed succeeded and its live dataset still exists.

    Import history may outlive the live tables after a manual truncate or a partial
    restore. In that state the cached archive must be promoted again even though
    its checksum has already succeeded.
    """

    try:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    EXISTS (
                        SELECT 1 FROM gtfs.feed_imports
                        WHERE operator = %s AND sha256 = %s AND status = 'succeeded'
                    )
                    AND EXISTS (SELECT 1 FROM gtfs.agency)
                    AND EXISTS (SELECT 1 FROM gtfs.routes)
                    AND EXISTS (SELECT 1 FROM gtfs.stops)
                    AND EXISTS (SELECT 1 FROM gtfs.trips)
                    AND EXISTS (SELECT 1 FROM gtfs.stop_times)
                """,
                (operator, sha256),
            )
            return bool(cursor.fetchone()[0])
    except psycopg.errors.UndefinedTable as exc:
        raise RuntimeError("The database is not migrated; run `alembic upgrade head` first") from exc


def import_feed(
    database_url: str,
    operator: str,
    feed: DownloadedFeed,
    validation: ValidationResult | None,
) -> ImportResult:
    import_id = _create_import_run(database_url, operator, feed, validation)
    try:
        return _load(database_url, operator, feed, import_id, validation)
    except Exception as exc:
        _fail_import(database_url, import_id, exc)
        raise


def _create_import_run(
    database_url: str,
    operator: str,
    feed: DownloadedFeed,
    validation: ValidationResult | None,
) -> int:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO gtfs.feed_imports (
                operator, source, sha256, etag, downloaded_at, status,
                validator_version, validation_report
            )
            VALUES (%s, %s, %s, %s, %s, 'running', %s, %s)
            RETURNING id
            """,
            (
                operator,
                feed.source,
                feed.sha256,
                feed.etag,
                feed.downloaded_at,
                validation.version if validation else None,
                Jsonb(validation.report) if validation else None,
            ),
        )
        return int(cursor.fetchone()[0])


def _load(
    database_url: str,
    operator: str,
    feed: DownloadedFeed,
    import_id: int,
    validation: ValidationResult | None,
) -> ImportResult:
    row_counts: dict[str, int] = {}
    ignored_columns: dict[str, list[str]] = {}

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s, hashtext(%s))", (ADVISORY_LOCK_NAMESPACE, operator))
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
        _truncate_staging(cursor)

        with FeedArchive(feed.path) as archive:
            for table in TABLES:
                if not archive.has(table.filename):
                    if table.required:
                        raise ValueError(f"GTFS input is missing required file {table.filename}")
                    row_counts[table.name] = 0
                    continue
                ignored_columns[table.name] = _load_table(cursor, archive, table)
                cursor.execute(
                    sql.SQL("SELECT count(*) FROM {}.{}").format(
                        sql.Identifier("gtfs_staging"), sql.Identifier(table.name)
                    )
                )
                row_counts[table.name] = int(cursor.fetchone()[0])

        _validate_staging(cursor, row_counts)
        feed_version = _feed_version(cursor)
        _promote(cursor)
        cursor.execute(
            """
            UPDATE gtfs.feed_imports
            SET status = 'succeeded', imported_at = now(), feed_version = %s,
                row_counts = %s, validator_version = %s
            WHERE id = %s
            """,
            (
                feed_version,
                Jsonb(row_counts),
                validation.version if validation else None,
                import_id,
            ),
        )

    return ImportResult(
        import_id=import_id,
        feed_version=feed_version,
        row_counts=row_counts,
        ignored_columns={name: columns for name, columns in ignored_columns.items() if columns},
    )


def _load_table(cursor: psycopg.Cursor, archive: FeedArchive, table: Table) -> list[str]:
    headers = archive.header(table.filename)
    if not headers:
        raise ValueError(f"{table.filename} has no CSV header")
    if len(headers) != len(set(headers)):
        raise ValueError(f"{table.filename} contains duplicate column names")
    invalid = [header for header in headers if not VALID_HEADER.fullmatch(header)]
    if invalid:
        raise ValueError(f"{table.filename} contains invalid column names: {invalid}")

    header_set = set(headers)
    missing = [field.source_name for field in table.fields if field.required and field.source_name not in header_set]
    if missing:
        raise ValueError(f"{table.filename} is missing required columns: {missing}")

    expected = {field.source_name for field in table.fields}
    ignored = sorted(header_set - expected)
    raw_table = f"raw_{table.name}"
    columns = sql.SQL(", ").join(sql.SQL("{} text").format(sql.Identifier(header)) for header in headers)
    cursor.execute(sql.SQL("CREATE TEMP TABLE {} ({}) ON COMMIT DROP").format(sql.Identifier(raw_table), columns))
    copy_statement = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)").format(
        sql.Identifier(raw_table),
        sql.SQL(", ").join(sql.Identifier(header) for header in headers),
    )
    with cursor.copy(copy_statement) as copy:
        for chunk in archive.chunks(table.filename):
            copy.write(chunk)

    target_columns = sql.SQL(", ").join(sql.Identifier(field.target) for field in table.fields)
    expressions = sql.SQL(", ").join(_field_expression(field, header_set) for field in table.fields)
    cursor.execute(
        sql.SQL("INSERT INTO {}.{} ({}) SELECT {} FROM {}").format(
            sql.Identifier("gtfs_staging"),
            sql.Identifier(table.name),
            target_columns,
            expressions,
            sql.Identifier(raw_table),
        )
    )
    return ignored


def _field_expression(field: Field, headers: set[str]) -> sql.Composed:
    pg_type = PG_TYPES[field.kind]
    if field.source_name not in headers:
        return sql.SQL("NULL::{}").format(sql.SQL(pg_type))

    column = sql.Identifier(field.source_name)
    if field.kind == "text":
        return sql.SQL("NULLIF({}, '')").format(column)
    if field.kind == "date":
        return sql.SQL("to_date(NULLIF({}, ''), 'YYYYMMDD')").format(column)
    if field.kind == "gtfs_time":
        return sql.SQL("gtfs.parse_time(NULLIF({}, ''))").format(column)
    return sql.SQL("NULLIF({}, '')::{}").format(column, sql.SQL(pg_type))


def _truncate_staging(cursor: psycopg.Cursor) -> None:
    tables = sql.SQL(", ").join(
        sql.SQL("{}.{}").format(sql.Identifier("gtfs_staging"), sql.Identifier(table.name)) for table in TABLES
    )
    cursor.execute(sql.SQL("TRUNCATE TABLE {}").format(tables))


def _validate_staging(cursor: psycopg.Cursor, row_counts: dict[str, int]) -> None:
    empty_required = [table.name for table in TABLES if table.required and row_counts.get(table.name, 0) == 0]
    if empty_required:
        raise ValueError(f"Required GTFS tables are empty: {empty_required}")

    checks = {
        "trips reference a missing route": """
            SELECT count(*) FROM gtfs_staging.trips t
            LEFT JOIN gtfs_staging.routes r ON r.route_id = t.route_id
            WHERE r.route_id IS NULL
        """,
        "trips reference a missing service": """
            SELECT count(*) FROM gtfs_staging.trips t
            WHERE NOT EXISTS (
                SELECT 1 FROM gtfs_staging.calendar c WHERE c.service_id = t.service_id
            ) AND NOT EXISTS (
                SELECT 1 FROM gtfs_staging.calendar_dates cd WHERE cd.service_id = t.service_id
            )
        """,
        "stop times reference a missing trip or stop": """
            SELECT count(*) FROM gtfs_staging.stop_times st
            LEFT JOIN gtfs_staging.trips t ON t.trip_id = st.trip_id
            LEFT JOIN gtfs_staging.stops s ON s.stop_id = st.stop_id
            WHERE t.trip_id IS NULL OR s.stop_id IS NULL
        """,
        "trips reference a missing shape": """
            SELECT count(*) FROM gtfs_staging.trips t
            WHERE t.shape_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM gtfs_staging.shapes s WHERE s.shape_id = t.shape_id
            )
        """,
    }
    for message, query in checks.items():
        cursor.execute(query)
        count = int(cursor.fetchone()[0])
        if count:
            raise ValueError(f"{count} {message}")


def _feed_version(cursor: psycopg.Cursor) -> str | None:
    cursor.execute("SELECT feed_version FROM gtfs_staging.feed_info LIMIT 1")
    row = cursor.fetchone()
    return str(row[0]) if row and row[0] is not None else None


def _promote(cursor: psycopg.Cursor) -> None:
    live_tables = sql.SQL(", ").join(
        sql.SQL("{}.{}").format(sql.Identifier("gtfs"), sql.Identifier(name)) for name in reversed(PROMOTION_ORDER)
    )
    cursor.execute(sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY").format(live_tables))

    for name in PROMOTION_ORDER:
        table = TABLE_BY_NAME[name]
        columns = sql.SQL(", ").join(sql.Identifier(field.target) for field in table.fields)
        cursor.execute(
            sql.SQL("INSERT INTO {}.{} ({}) SELECT {} FROM {}.{}").format(
                sql.Identifier("gtfs"),
                sql.Identifier(name),
                columns,
                columns,
                sql.Identifier("gtfs_staging"),
                sql.Identifier(name),
            )
        )
        cursor.execute(sql.SQL("ANALYZE {}.{}").format(sql.Identifier("gtfs"), sql.Identifier(name)))


def _fail_import(database_url: str, import_id: int, error: Exception) -> None:
    try:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE gtfs.feed_imports
                SET status = 'failed', imported_at = now(), error_message = %s
                WHERE id = %s
                """,
                (str(error)[:4000], import_id),
            )
    except Exception:
        # Preserve the original import exception if recording the failure also fails.
        logger.exception("Could not record failed GTFS import %s", import_id)
