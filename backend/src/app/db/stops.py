import psycopg
from psycopg.rows import class_row

from app.models import Page, StopSummary


def get_stops(connection: psycopg.Connection, *, limit: int = 100, offset: int = 0) -> Page[StopSummary]:
    """Return a page of GTFS stops ordered by name and identifier."""

    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM gtfs.stops_with_display_name")
        total = int(cursor.fetchone()[0])

    with connection.cursor(row_factory=class_row(StopSummary)) as cursor:
        cursor.execute(
            """
            SELECT
                stop_id,
                display_name,
                location_type
            FROM gtfs.stops_with_display_name
            WHERE location_type = 1
            ORDER BY display_name NULLS LAST, stop_id
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        items = cursor.fetchall()

    return Page(items=items, total=total, limit=limit, offset=offset)
