import psycopg
from psycopg.rows import class_row

from app.models import Page, Stop


def get_stops(connection: psycopg.Connection, *, limit: int = 100, offset: int = 0) -> Page[Stop]:
    """Return a page of GTFS stops ordered by name and identifier."""

    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM gtfs.stops")
        total = int(cursor.fetchone()[0])

    with connection.cursor(row_factory=class_row(Stop)) as cursor:
        cursor.execute(
            """
            SELECT
                stop_id,
                stop_name,
                stop_lat,
                stop_lon,
                location_type,
                parent_station,
                platform_code
            FROM gtfs.stops
            ORDER BY stop_name NULLS LAST, stop_id
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        items = cursor.fetchall()

    return Page(items=items, total=total, limit=limit, offset=offset)
