from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def foreign_key(target: str) -> ForeignKey:
    return ForeignKey(target, deferrable=True, initially="DEFERRED")


class FeedImport(Base):
    __tablename__ = "feed_imports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'unchanged')",
            name="feed_imports_status_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    operator: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    feed_version: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(Text)
    etag: Mapped[str | None] = mapped_column(Text)
    downloaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    validator_version: Mapped[str | None] = mapped_column(Text)
    row_counts: Mapped[dict[str, int] | None] = mapped_column(JSONB)
    validation_report: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)


Index(
    "feed_imports_operator_imported_idx",
    FeedImport.__table__.c.operator,
    FeedImport.__table__.c.imported_at.desc(),
)
Index("feed_imports_sha256_idx", FeedImport.__table__.c.operator, FeedImport.__table__.c.sha256)


class Agency(Base):
    __tablename__ = "agency"

    agency_id: Mapped[str] = mapped_column(Text, primary_key=True)
    agency_name: Mapped[str] = mapped_column(Text)
    agency_url: Mapped[str] = mapped_column(Text)
    agency_timezone: Mapped[str] = mapped_column(Text)
    agency_lang: Mapped[str | None] = mapped_column(Text)
    agency_fare_url: Mapped[str | None] = mapped_column(Text)

    routes: Mapped[list[Route]] = relationship(back_populates="agency")


class BookingRule(Base):
    __tablename__ = "booking_rules"
    __table_args__ = (
        CheckConstraint("prior_notice_duration_min >= 0", name="booking_rules_duration_check"),
        CheckConstraint("prior_notice_last_day >= 0", name="booking_rules_last_day_check"),
        CheckConstraint("prior_notice_last_time >= 0", name="booking_rules_last_time_check"),
    )

    booking_rule_id: Mapped[str] = mapped_column(Text, primary_key=True)
    booking_type: Mapped[int] = mapped_column(SmallInteger)
    prior_notice_duration_min: Mapped[int | None] = mapped_column(Integer)
    prior_notice_last_day: Mapped[int | None] = mapped_column(Integer)
    prior_notice_last_time: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    phone_number: Mapped[str | None] = mapped_column(Text)


class Calendar(Base):
    __tablename__ = "calendar"
    __table_args__ = (CheckConstraint("start_date <= end_date", name="calendar_date_range_check"),)

    service_id: Mapped[str] = mapped_column(Text, primary_key=True)
    monday: Mapped[bool] = mapped_column(Boolean)
    tuesday: Mapped[bool] = mapped_column(Boolean)
    wednesday: Mapped[bool] = mapped_column(Boolean)
    thursday: Mapped[bool] = mapped_column(Boolean)
    friday: Mapped[bool] = mapped_column(Boolean)
    saturday: Mapped[bool] = mapped_column(Boolean)
    sunday: Mapped[bool] = mapped_column(Boolean)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)


class CalendarDate(Base):
    __tablename__ = "calendar_dates"
    __table_args__ = (
        CheckConstraint("exception_type IN (1, 2)", name="calendar_dates_exception_type_check"),
        Index("calendar_dates_date_service_idx", "date", "service_id"),
    )

    service_id: Mapped[str] = mapped_column(Text, primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    exception_type: Mapped[int] = mapped_column(SmallInteger)


class FeedInfo(Base):
    __tablename__ = "feed_info"
    __table_args__ = (
        CheckConstraint(
            "feed_start_date IS NULL OR feed_end_date IS NULL OR feed_start_date <= feed_end_date",
            name="feed_info_date_range_check",
        ),
    )

    feed_id: Mapped[str] = mapped_column(Text, primary_key=True)
    feed_publisher_name: Mapped[str] = mapped_column(Text)
    feed_publisher_url: Mapped[str] = mapped_column(Text)
    feed_lang: Mapped[str] = mapped_column(Text)
    feed_version: Mapped[str | None] = mapped_column(Text)
    feed_start_date: Mapped[date | None] = mapped_column(Date)
    feed_end_date: Mapped[date | None] = mapped_column(Date)


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        CheckConstraint("route_type >= 0", name="routes_type_check"),
        Index("routes_agency_idx", "agency_id"),
    )

    route_id: Mapped[str] = mapped_column(Text, primary_key=True)
    agency_id: Mapped[str | None] = mapped_column(Text, foreign_key("gtfs.agency.agency_id"))
    route_short_name: Mapped[str | None] = mapped_column(Text)
    route_long_name: Mapped[str | None] = mapped_column(Text)
    route_type: Mapped[int] = mapped_column(Integer)
    route_desc: Mapped[str | None] = mapped_column(Text)

    agency: Mapped[Agency | None] = relationship(back_populates="routes")
    trips: Mapped[list[Trip]] = relationship(back_populates="route")


class Stop(Base):
    __tablename__ = "stops"
    __table_args__ = (
        CheckConstraint("stop_lat BETWEEN -90 AND 90", name="stops_latitude_check"),
        CheckConstraint("stop_lon BETWEEN -180 AND 180", name="stops_longitude_check"),
        CheckConstraint("location_type BETWEEN 0 AND 4", name="stops_location_type_check"),
        Index("stops_parent_station_idx", "parent_station"),
    )

    stop_id: Mapped[str] = mapped_column(Text, primary_key=True)
    stop_name: Mapped[str | None] = mapped_column(Text)
    stop_lat: Mapped[float | None] = mapped_column(Double)
    stop_lon: Mapped[float | None] = mapped_column(Double)
    location_type: Mapped[int | None] = mapped_column(SmallInteger)
    parent_station: Mapped[str | None] = mapped_column(Text, foreign_key("gtfs.stops.stop_id"))
    platform_code: Mapped[str | None] = mapped_column(Text)


class Shape(Base):
    __tablename__ = "shapes"
    __table_args__ = (
        CheckConstraint("shape_pt_lat BETWEEN -90 AND 90", name="shapes_latitude_check"),
        CheckConstraint("shape_pt_lon BETWEEN -180 AND 180", name="shapes_longitude_check"),
        CheckConstraint("shape_pt_sequence >= 0", name="shapes_sequence_check"),
        CheckConstraint("shape_dist_traveled >= 0", name="shapes_distance_check"),
    )

    shape_id: Mapped[str] = mapped_column(Text, primary_key=True)
    shape_pt_lat: Mapped[float] = mapped_column(Double)
    shape_pt_lon: Mapped[float] = mapped_column(Double)
    shape_pt_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    shape_dist_traveled: Mapped[float | None] = mapped_column(Double)


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint("direction_id IN (0, 1)", name="trips_direction_check"),
        Index("trips_route_idx", "route_id"),
        Index("trips_service_idx", "service_id"),
        Index("trips_shape_idx", "shape_id"),
    )

    route_id: Mapped[str] = mapped_column(Text, foreign_key("gtfs.routes.route_id"))
    service_id: Mapped[str] = mapped_column(Text)
    trip_id: Mapped[str] = mapped_column(Text, primary_key=True)
    trip_headsign: Mapped[str | None] = mapped_column(Text)
    trip_short_name: Mapped[str | None] = mapped_column(Text)
    direction_id: Mapped[int | None] = mapped_column(SmallInteger)
    shape_id: Mapped[str | None] = mapped_column(Text)
    samtrafiken_internal_trip_number: Mapped[str | None] = mapped_column(Text)

    route: Mapped[Route] = relationship(back_populates="trips")
    stop_times: Mapped[list[StopTime]] = relationship(back_populates="trip")


class StopTime(Base):
    __tablename__ = "stop_times"
    __table_args__ = (
        CheckConstraint("arrival_seconds >= 0", name="stop_times_arrival_check"),
        CheckConstraint("departure_seconds >= 0", name="stop_times_departure_check"),
        CheckConstraint("stop_sequence >= 0", name="stop_times_sequence_check"),
        CheckConstraint("pickup_type BETWEEN 0 AND 3", name="stop_times_pickup_type_check"),
        CheckConstraint("drop_off_type BETWEEN 0 AND 3", name="stop_times_drop_off_type_check"),
        CheckConstraint("shape_dist_traveled >= 0", name="stop_times_distance_check"),
        CheckConstraint("timepoint IN (0, 1)", name="stop_times_timepoint_check"),
        Index("stop_times_stop_idx", "stop_id"),
        Index("stop_times_stop_departure_idx", "stop_id", "departure_seconds"),
    )

    trip_id: Mapped[str] = mapped_column(Text, foreign_key("gtfs.trips.trip_id"), primary_key=True)
    arrival_seconds: Mapped[int | None] = mapped_column(Integer)
    departure_seconds: Mapped[int | None] = mapped_column(Integer)
    stop_id: Mapped[str] = mapped_column(Text, foreign_key("gtfs.stops.stop_id"))
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_headsign: Mapped[str | None] = mapped_column(Text)
    pickup_type: Mapped[int | None] = mapped_column(SmallInteger)
    drop_off_type: Mapped[int | None] = mapped_column(SmallInteger)
    shape_dist_traveled: Mapped[float | None] = mapped_column(Double)
    timepoint: Mapped[int | None] = mapped_column(SmallInteger)
    pickup_booking_rule_id: Mapped[str | None] = mapped_column(Text, foreign_key("gtfs.booking_rules.booking_rule_id"))
    drop_off_booking_rule_id: Mapped[str | None] = mapped_column(
        Text, foreign_key("gtfs.booking_rules.booking_rule_id")
    )

    trip: Mapped[Trip] = relationship(back_populates="stop_times")


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint("transfer_type BETWEEN 0 AND 5", name="transfers_type_check"),
        CheckConstraint("min_transfer_time >= 0", name="transfers_minimum_time_check"),
        Index("transfers_from_stop_idx", "from_stop_id"),
        Index("transfers_to_stop_idx", "to_stop_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    from_stop_id: Mapped[str] = mapped_column(Text, foreign_key("gtfs.stops.stop_id"))
    to_stop_id: Mapped[str] = mapped_column(Text, foreign_key("gtfs.stops.stop_id"))
    transfer_type: Mapped[int] = mapped_column(SmallInteger)
    min_transfer_time: Mapped[int | None] = mapped_column(Integer)
    from_trip_id: Mapped[str | None] = mapped_column(Text, foreign_key("gtfs.trips.trip_id"))
    to_trip_id: Mapped[str | None] = mapped_column(Text, foreign_key("gtfs.trips.trip_id"))


class Attribution(Base):
    __tablename__ = "attributions"
    __table_args__ = (Index("attributions_trip_idx", "trip_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    trip_id: Mapped[str | None] = mapped_column(Text, foreign_key("gtfs.trips.trip_id"))
    organization_name: Mapped[str] = mapped_column(Text)
    is_operator: Mapped[bool | None] = mapped_column(Boolean)
