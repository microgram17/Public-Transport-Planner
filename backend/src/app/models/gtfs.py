from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DatabaseModel(BaseModel):
    """Base for validated rows returned by Psycopg repositories."""

    model_config = ConfigDict(extra="forbid")


class FeedImport(DatabaseModel):
    id: int
    operator: str
    source: str
    feed_version: str | None = None
    sha256: str
    etag: str | None = None
    downloaded_at: dt.datetime
    imported_at: dt.datetime | None = None
    status: Literal["running", "succeeded", "failed", "unchanged"]
    validator_version: str | None = None
    row_counts: dict[str, int] | None = None
    validation_report: dict[str, Any] | None = None
    error_message: str | None = None


class Agency(DatabaseModel):
    agency_id: str
    agency_name: str
    agency_url: str
    agency_timezone: str
    agency_lang: str | None = None
    agency_fare_url: str | None = None


class BookingRule(DatabaseModel):
    booking_rule_id: str
    booking_type: int
    prior_notice_duration_min: int | None = Field(default=None, ge=0)
    prior_notice_last_day: int | None = Field(default=None, ge=0)
    prior_notice_last_time: int | None = Field(default=None, ge=0)
    message: str | None = None
    phone_number: str | None = None


class Calendar(DatabaseModel):
    service_id: str
    monday: bool
    tuesday: bool
    wednesday: bool
    thursday: bool
    friday: bool
    saturday: bool
    sunday: bool
    start_date: dt.date
    end_date: dt.date


class CalendarDate(DatabaseModel):
    service_id: str
    date: dt.date
    exception_type: Literal[1, 2]


class FeedInfo(DatabaseModel):
    feed_id: str
    feed_publisher_name: str
    feed_publisher_url: str
    feed_lang: str
    feed_version: str | None = None
    feed_start_date: dt.date | None = None
    feed_end_date: dt.date | None = None


class Route(DatabaseModel):
    route_id: str
    agency_id: str | None = None
    route_short_name: str | None = None
    route_long_name: str | None = None
    route_type: int = Field(ge=0)
    route_desc: str | None = None


class Stop(DatabaseModel):
    stop_id: str
    stop_name: str | None = None
    stop_lat: float | None = Field(default=None, ge=-90, le=90)
    stop_lon: float | None = Field(default=None, ge=-180, le=180)
    location_type: int | None = Field(default=None, ge=0, le=4)
    parent_station: str | None = None
    platform_code: str | None = None


class Shape(DatabaseModel):
    shape_id: str
    shape_pt_lat: float = Field(ge=-90, le=90)
    shape_pt_lon: float = Field(ge=-180, le=180)
    shape_pt_sequence: int = Field(ge=0)
    shape_dist_traveled: float | None = Field(default=None, ge=0)


class Trip(DatabaseModel):
    route_id: str
    service_id: str
    trip_id: str
    trip_headsign: str | None = None
    trip_short_name: str | None = None
    direction_id: Literal[0, 1] | None = None
    shape_id: str | None = None
    samtrafiken_internal_trip_number: str | None = None


class StopTime(DatabaseModel):
    trip_id: str
    arrival_seconds: int | None = Field(default=None, ge=0)
    departure_seconds: int | None = Field(default=None, ge=0)
    stop_id: str
    stop_sequence: int = Field(ge=0)
    stop_headsign: str | None = None
    pickup_type: int | None = Field(default=None, ge=0, le=3)
    drop_off_type: int | None = Field(default=None, ge=0, le=3)
    shape_dist_traveled: float | None = Field(default=None, ge=0)
    timepoint: Literal[0, 1] | None = None
    pickup_booking_rule_id: str | None = None
    drop_off_booking_rule_id: str | None = None


class Transfer(DatabaseModel):
    id: int
    from_stop_id: str
    to_stop_id: str
    transfer_type: int = Field(ge=0, le=5)
    min_transfer_time: int | None = Field(default=None, ge=0)
    from_trip_id: str | None = None
    to_trip_id: str | None = None


class Attribution(DatabaseModel):
    id: int
    trip_id: str | None = None
    organization_name: str
    is_operator: bool | None = None


GTFS_MODELS: dict[str, type[DatabaseModel]] = {
    "agency": Agency,
    "booking_rules": BookingRule,
    "calendar": Calendar,
    "calendar_dates": CalendarDate,
    "feed_info": FeedInfo,
    "routes": Route,
    "stops": Stop,
    "shapes": Shape,
    "trips": Trip,
    "stop_times": StopTime,
    "transfers": Transfer,
    "attributions": Attribution,
}
