import psycopg
from psycopg.rows import class_row

from app.models import Departure

# TODO: Need to add pagination in the future, probably do like 5 at a time, but its fine for now


def get_departures_for_station(
    connection: psycopg.Connection,
    *,
    station_id: str,
) -> list[Departure]:
    query = """
        WITH station_stops AS (
            SELECT stop_id
            FROM gtfs.stops
            WHERE stop_id = %s
               OR parent_station = %s
        )
        SELECT
            stop_times.stop_id,
            stops.stop_name,
            stops.platform_code,

            stop_times.trip_id,
            trips.trip_headsign,

            routes.route_id,
            routes.route_short_name,
            routes.route_long_name,

            stop_times.arrival_seconds,
            stop_times.departure_seconds
        FROM gtfs.stop_times AS stop_times
        JOIN station_stops
            ON station_stops.stop_id = stop_times.stop_id
        JOIN gtfs.stops AS stops
            ON stops.stop_id = stop_times.stop_id
        JOIN gtfs.trips AS trips
            ON trips.trip_id = stop_times.trip_id
        JOIN gtfs.routes AS routes
            ON routes.route_id = trips.route_id
        WHERE stop_times.departure_seconds IS NOT NULL
          AND COALESCE(stop_times.pickup_type, 0) <> 1
        ORDER BY
            stop_times.departure_seconds,
            stops.platform_code NULLS LAST,
            routes.route_short_name NULLS LAST
    """

    with connection.cursor(row_factory=class_row(Departure)) as cursor:
        cursor.execute(query, (station_id, station_id))
        return cursor.fetchall()
