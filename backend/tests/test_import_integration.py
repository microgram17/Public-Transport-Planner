from __future__ import annotations

import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import psycopg
import pytest

from app.gtfs.download import local_feed
from app.gtfs.loader import import_feed, was_imported


def make_feed(path: Path, *, include_stops: bool = True) -> Path:
    files = {
        "agency.txt": (
            "agency_id,agency_name,agency_url,agency_timezone,agency_lang,agency_fare_url\n"
            "agency,Test Agency,https://example.com,Europe/Stockholm,sv,\n"
        ),
        "calendar.txt": (
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
            "weekday,1,1,1,1,1,0,0,20260101,20261231\n"
        ),
        "calendar_dates.txt": "service_id,date,exception_type\nweekday,20260619,2\n",
        "feed_info.txt": (
            "feed_id,feed_publisher_name,feed_publisher_url,feed_lang,feed_version\n"
            "test,Publisher,https://example.com,sv,fixture-1\n"
        ),
        "routes.txt": (
            "route_id,agency_id,route_short_name,route_long_name,route_type,route_desc\n"
            "route,agency,1,Test route,700,\n"
        ),
        "shapes.txt": (
            "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence,shape_dist_traveled\n"
            "shape,59.3,18.0,1,0\nshape,59.4,18.1,2,1000\n"
        ),
        "trips.txt": (
            "route_id,service_id,trip_id,trip_headsign,trip_short_name,direction_id,shape_id,"
            "samtrafiken_internal_trip_number\n"
            "route,weekday,trip,Centralen,,0,shape,internal-1\n"
        ),
        "stop_times.txt": (
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence,stop_headsign,pickup_type,"
            "drop_off_type,shape_dist_traveled,timepoint,pickup_booking_rule_id,drop_off_booking_rule_id\n"
            "trip,25:15:00,25:15:00,stop-a,1,,0,0,0,1,,\n"
            "trip,25:20:00,25:20:00,stop-b,2,,0,0,1000,1,,\n"
        ),
    }
    if include_stops:
        files["stops.txt"] = (
            "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station,platform_code\n"
            "station,Test station,59.3,18.0,1,,\n"
            "stop-a,Platform A,59.3,18.0,0,station,A\n"
            "stop-b,Platform B,59.4,18.1,0,station,B\n"
        )

    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)
    return path


@pytest.mark.integration
def test_import_is_repeatable_and_failure_preserves_live_data(tmp_path: Path) -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set")

    good = local_feed(make_feed(tmp_path / "good.zip"))
    first = import_feed(database_url, "test", good, validation=None)
    second = import_feed(database_url, "test", good, validation=None)

    assert first.row_counts["stop_times"] == 2
    assert second.row_counts == first.row_counts
    assert was_imported(database_url, "test", good.sha256)
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT arrival_seconds FROM gtfs.stop_times WHERE trip_id = 'trip' AND stop_sequence = 1")
        assert cursor.fetchone()[0] == 25 * 3600 + 15 * 60

        cursor.execute(
            """
            TRUNCATE TABLE
                gtfs.attributions, gtfs.transfers, gtfs.stop_times, gtfs.trips,
                gtfs.shapes, gtfs.stops, gtfs.routes, gtfs.feed_info,
                gtfs.calendar_dates, gtfs.calendar, gtfs.booking_rules, gtfs.agency
            RESTART IDENTITY
            """
        )

    assert not was_imported(database_url, "test", good.sha256)
    restored = import_feed(database_url, "test", good, validation=None)
    assert restored.row_counts == first.row_counts

    bad = local_feed(make_feed(tmp_path / "bad.zip", include_stops=False))
    with pytest.raises(ValueError, match="missing required file stops.txt"):
        import_feed(database_url, "test", bad, validation=None)

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM gtfs.stop_times")
        assert cursor.fetchone()[0] == 2
