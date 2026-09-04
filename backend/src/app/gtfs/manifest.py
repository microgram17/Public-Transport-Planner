from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    target: str
    kind: str = "text"
    source: str | None = None
    required: bool = False

    @property
    def source_name(self) -> str:
        return self.source or self.target


@dataclass(frozen=True)
class Table:
    name: str
    fields: tuple[Field, ...]
    required: bool = False

    @property
    def filename(self) -> str:
        return f"{self.name}.txt"


def f(target: str, kind: str = "text", *, source: str | None = None, required: bool = False) -> Field:
    return Field(target=target, kind=kind, source=source, required=required)


TABLES = (
    Table(
        "agency",
        (
            f("agency_id", required=True),
            f("agency_name", required=True),
            f("agency_url", required=True),
            f("agency_timezone", required=True),
            f("agency_lang"),
            f("agency_fare_url"),
        ),
        required=True,
    ),
    Table(
        "booking_rules",
        (
            f("booking_rule_id", required=True),
            f("booking_type", "smallint", required=True),
            f("prior_notice_duration_min", "integer"),
            f("prior_notice_last_day", "integer"),
            f("prior_notice_last_time", "gtfs_time"),
            f("message"),
            f("phone_number"),
        ),
    ),
    Table(
        "calendar",
        (
            f("service_id", required=True),
            f("monday", "boolean", required=True),
            f("tuesday", "boolean", required=True),
            f("wednesday", "boolean", required=True),
            f("thursday", "boolean", required=True),
            f("friday", "boolean", required=True),
            f("saturday", "boolean", required=True),
            f("sunday", "boolean", required=True),
            f("start_date", "date", required=True),
            f("end_date", "date", required=True),
        ),
        required=True,
    ),
    Table(
        "calendar_dates",
        (
            f("service_id", required=True),
            f("date", "date", required=True),
            f("exception_type", "smallint", required=True),
        ),
        required=True,
    ),
    Table(
        "feed_info",
        (
            f("feed_id", required=True),
            f("feed_publisher_name", required=True),
            f("feed_publisher_url", required=True),
            f("feed_lang", required=True),
            f("feed_version"),
            f("feed_start_date", "date"),
            f("feed_end_date", "date"),
        ),
    ),
    Table(
        "routes",
        (
            f("route_id", required=True),
            f("agency_id"),
            f("route_short_name"),
            f("route_long_name"),
            f("route_type", "integer", required=True),
            f("route_desc"),
        ),
        required=True,
    ),
    Table(
        "stops",
        (
            f("stop_id", required=True),
            f("stop_name"),
            f("stop_lat", "double"),
            f("stop_lon", "double"),
            f("location_type", "smallint"),
            f("parent_station"),
            f("platform_code"),
        ),
        required=True,
    ),
    Table(
        "shapes",
        (
            f("shape_id", required=True),
            f("shape_pt_lat", "double", required=True),
            f("shape_pt_lon", "double", required=True),
            f("shape_pt_sequence", "integer", required=True),
            f("shape_dist_traveled", "double"),
        ),
    ),
    Table(
        "trips",
        (
            f("route_id", required=True),
            f("service_id", required=True),
            f("trip_id", required=True),
            f("trip_headsign"),
            f("trip_short_name"),
            f("direction_id", "smallint"),
            f("shape_id"),
            f("samtrafiken_internal_trip_number"),
        ),
        required=True,
    ),
    Table(
        "stop_times",
        (
            f("trip_id", required=True),
            f("arrival_seconds", "gtfs_time", source="arrival_time"),
            f("departure_seconds", "gtfs_time", source="departure_time"),
            f("stop_id", required=True),
            f("stop_sequence", "integer", required=True),
            f("stop_headsign"),
            f("pickup_type", "smallint"),
            f("drop_off_type", "smallint"),
            f("shape_dist_traveled", "double"),
            f("timepoint", "smallint"),
            f("pickup_booking_rule_id"),
            f("drop_off_booking_rule_id"),
        ),
        required=True,
    ),
    Table(
        "transfers",
        (
            f("from_stop_id", required=True),
            f("to_stop_id", required=True),
            f("transfer_type", "smallint", required=True),
            f("min_transfer_time", "integer"),
            f("from_trip_id"),
            f("to_trip_id"),
        ),
    ),
    Table(
        "attributions",
        (
            f("trip_id"),
            f("organization_name", required=True),
            f("is_operator", "boolean"),
        ),
    ),
)

TABLE_BY_NAME = {table.name: table for table in TABLES}

# This order satisfies the live tables' foreign keys.
PROMOTION_ORDER = (
    "agency",
    "booking_rules",
    "calendar",
    "calendar_dates",
    "feed_info",
    "routes",
    "stops",
    "shapes",
    "trips",
    "stop_times",
    "transfers",
    "attributions",
)
