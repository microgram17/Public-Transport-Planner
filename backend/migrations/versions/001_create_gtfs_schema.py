"""Create typed GTFS and staging schemas.

Revision ID: 001
Revises: None
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

GTFS_SCHEMA = "gtfs"
STAGING_SCHEMA = "gtfs_staging"
GTFS_TABLES = (
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

PARSE_TIME_FUNCTION = r"""
CREATE FUNCTION gtfs.parse_time(value text)
RETURNS integer
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
DECLARE
    parts text[];
BEGIN
    IF value !~ '^[0-9]{2,3}:[0-5][0-9]:[0-5][0-9]$' THEN
        RAISE EXCEPTION 'invalid GTFS time: %', value;
    END IF;
    parts := string_to_array(value, ':');
    RETURN parts[1]::integer * 3600 + parts[2]::integer * 60 + parts[3]::integer;
END;
$$
"""


def gtfs_fk(column: str) -> sa.ForeignKey:
    return sa.ForeignKey(f"gtfs.{column}", deferrable=True, initially="DEFERRED")


def upgrade() -> None:
    op.execute(sa.schema.CreateSchema(GTFS_SCHEMA))
    op.execute(sa.schema.CreateSchema(STAGING_SCHEMA))
    op.execute(PARSE_TIME_FUNCTION)

    op.create_table(
        "feed_imports",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("operator", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("feed_version", sa.Text()),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("etag", sa.Text()),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("validator_version", sa.Text()),
        sa.Column("row_counts", postgresql.JSONB()),
        sa.Column("validation_report", postgresql.JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'unchanged')",
            name="feed_imports_status_check",
        ),
        schema=GTFS_SCHEMA,
    )
    op.create_index(
        "feed_imports_operator_imported_idx",
        "feed_imports",
        ["operator", sa.text("imported_at DESC")],
        schema=GTFS_SCHEMA,
    )
    op.create_index("feed_imports_sha256_idx", "feed_imports", ["operator", "sha256"], schema=GTFS_SCHEMA)

    op.create_table(
        "agency",
        sa.Column("agency_id", sa.Text(), primary_key=True),
        sa.Column("agency_name", sa.Text(), nullable=False),
        sa.Column("agency_url", sa.Text(), nullable=False),
        sa.Column("agency_timezone", sa.Text(), nullable=False),
        sa.Column("agency_lang", sa.Text()),
        sa.Column("agency_fare_url", sa.Text()),
        schema=GTFS_SCHEMA,
    )

    op.create_table(
        "booking_rules",
        sa.Column("booking_rule_id", sa.Text(), primary_key=True),
        sa.Column("booking_type", sa.SmallInteger(), nullable=False),
        sa.Column("prior_notice_duration_min", sa.Integer()),
        sa.Column("prior_notice_last_day", sa.Integer()),
        sa.Column("prior_notice_last_time", sa.Integer()),
        sa.Column("message", sa.Text()),
        sa.Column("phone_number", sa.Text()),
        sa.CheckConstraint("prior_notice_duration_min >= 0", name="booking_rules_duration_check"),
        sa.CheckConstraint("prior_notice_last_day >= 0", name="booking_rules_last_day_check"),
        sa.CheckConstraint("prior_notice_last_time >= 0", name="booking_rules_last_time_check"),
        schema=GTFS_SCHEMA,
    )

    op.create_table(
        "calendar",
        sa.Column("service_id", sa.Text(), primary_key=True),
        sa.Column("monday", sa.Boolean(), nullable=False),
        sa.Column("tuesday", sa.Boolean(), nullable=False),
        sa.Column("wednesday", sa.Boolean(), nullable=False),
        sa.Column("thursday", sa.Boolean(), nullable=False),
        sa.Column("friday", sa.Boolean(), nullable=False),
        sa.Column("saturday", sa.Boolean(), nullable=False),
        sa.Column("sunday", sa.Boolean(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.CheckConstraint("start_date <= end_date", name="calendar_date_range_check"),
        schema=GTFS_SCHEMA,
    )

    op.create_table(
        "calendar_dates",
        sa.Column("service_id", sa.Text(), primary_key=True),
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("exception_type", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("exception_type IN (1, 2)", name="calendar_dates_exception_type_check"),
        schema=GTFS_SCHEMA,
    )
    op.create_index(
        "calendar_dates_date_service_idx",
        "calendar_dates",
        ["date", "service_id"],
        schema=GTFS_SCHEMA,
    )

    op.create_table(
        "feed_info",
        sa.Column("feed_id", sa.Text(), primary_key=True),
        sa.Column("feed_publisher_name", sa.Text(), nullable=False),
        sa.Column("feed_publisher_url", sa.Text(), nullable=False),
        sa.Column("feed_lang", sa.Text(), nullable=False),
        sa.Column("feed_version", sa.Text()),
        sa.Column("feed_start_date", sa.Date()),
        sa.Column("feed_end_date", sa.Date()),
        sa.CheckConstraint(
            "feed_start_date IS NULL OR feed_end_date IS NULL OR feed_start_date <= feed_end_date",
            name="feed_info_date_range_check",
        ),
        schema=GTFS_SCHEMA,
    )

    op.create_table(
        "routes",
        sa.Column("route_id", sa.Text(), primary_key=True),
        sa.Column("agency_id", sa.Text(), gtfs_fk("agency.agency_id")),
        sa.Column("route_short_name", sa.Text()),
        sa.Column("route_long_name", sa.Text()),
        sa.Column("route_type", sa.Integer(), nullable=False),
        sa.Column("route_desc", sa.Text()),
        sa.CheckConstraint("route_type >= 0", name="routes_type_check"),
        schema=GTFS_SCHEMA,
    )
    op.create_index("routes_agency_idx", "routes", ["agency_id"], schema=GTFS_SCHEMA)

    op.create_table(
        "stops",
        sa.Column("stop_id", sa.Text(), primary_key=True),
        sa.Column("stop_name", sa.Text()),
        sa.Column("stop_lat", sa.Double()),
        sa.Column("stop_lon", sa.Double()),
        sa.Column("location_type", sa.SmallInteger()),
        sa.Column("parent_station", sa.Text(), gtfs_fk("stops.stop_id")),
        sa.Column("platform_code", sa.Text()),
        sa.CheckConstraint("stop_lat BETWEEN -90 AND 90", name="stops_latitude_check"),
        sa.CheckConstraint("stop_lon BETWEEN -180 AND 180", name="stops_longitude_check"),
        sa.CheckConstraint("location_type BETWEEN 0 AND 4", name="stops_location_type_check"),
        schema=GTFS_SCHEMA,
    )
    op.create_index("stops_parent_station_idx", "stops", ["parent_station"], schema=GTFS_SCHEMA)

    op.create_table(
        "shapes",
        sa.Column("shape_id", sa.Text(), primary_key=True),
        sa.Column("shape_pt_lat", sa.Double(), nullable=False),
        sa.Column("shape_pt_lon", sa.Double(), nullable=False),
        sa.Column("shape_pt_sequence", sa.Integer(), primary_key=True),
        sa.Column("shape_dist_traveled", sa.Double()),
        sa.CheckConstraint("shape_pt_lat BETWEEN -90 AND 90", name="shapes_latitude_check"),
        sa.CheckConstraint("shape_pt_lon BETWEEN -180 AND 180", name="shapes_longitude_check"),
        sa.CheckConstraint("shape_pt_sequence >= 0", name="shapes_sequence_check"),
        sa.CheckConstraint("shape_dist_traveled >= 0", name="shapes_distance_check"),
        schema=GTFS_SCHEMA,
    )

    op.create_table(
        "trips",
        sa.Column("route_id", sa.Text(), gtfs_fk("routes.route_id"), nullable=False),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("trip_id", sa.Text(), primary_key=True),
        sa.Column("trip_headsign", sa.Text()),
        sa.Column("trip_short_name", sa.Text()),
        sa.Column("direction_id", sa.SmallInteger()),
        sa.Column("shape_id", sa.Text()),
        sa.Column("samtrafiken_internal_trip_number", sa.Text()),
        sa.CheckConstraint("direction_id IN (0, 1)", name="trips_direction_check"),
        schema=GTFS_SCHEMA,
    )
    op.create_index("trips_route_idx", "trips", ["route_id"], schema=GTFS_SCHEMA)
    op.create_index("trips_service_idx", "trips", ["service_id"], schema=GTFS_SCHEMA)
    op.create_index("trips_shape_idx", "trips", ["shape_id"], schema=GTFS_SCHEMA)

    op.create_table(
        "stop_times",
        sa.Column("trip_id", sa.Text(), gtfs_fk("trips.trip_id"), primary_key=True),
        sa.Column("arrival_seconds", sa.Integer()),
        sa.Column("departure_seconds", sa.Integer()),
        sa.Column("stop_id", sa.Text(), gtfs_fk("stops.stop_id"), nullable=False),
        sa.Column("stop_sequence", sa.Integer(), primary_key=True),
        sa.Column("stop_headsign", sa.Text()),
        sa.Column("pickup_type", sa.SmallInteger()),
        sa.Column("drop_off_type", sa.SmallInteger()),
        sa.Column("shape_dist_traveled", sa.Double()),
        sa.Column("timepoint", sa.SmallInteger()),
        sa.Column("pickup_booking_rule_id", sa.Text(), gtfs_fk("booking_rules.booking_rule_id")),
        sa.Column("drop_off_booking_rule_id", sa.Text(), gtfs_fk("booking_rules.booking_rule_id")),
        sa.CheckConstraint("arrival_seconds >= 0", name="stop_times_arrival_check"),
        sa.CheckConstraint("departure_seconds >= 0", name="stop_times_departure_check"),
        sa.CheckConstraint("stop_sequence >= 0", name="stop_times_sequence_check"),
        sa.CheckConstraint("pickup_type BETWEEN 0 AND 3", name="stop_times_pickup_type_check"),
        sa.CheckConstraint("drop_off_type BETWEEN 0 AND 3", name="stop_times_drop_off_type_check"),
        sa.CheckConstraint("shape_dist_traveled >= 0", name="stop_times_distance_check"),
        sa.CheckConstraint("timepoint IN (0, 1)", name="stop_times_timepoint_check"),
        schema=GTFS_SCHEMA,
    )
    op.create_index("stop_times_stop_idx", "stop_times", ["stop_id"], schema=GTFS_SCHEMA)
    op.create_index(
        "stop_times_stop_departure_idx",
        "stop_times",
        ["stop_id", "departure_seconds"],
        schema=GTFS_SCHEMA,
    )

    op.create_table(
        "transfers",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("from_stop_id", sa.Text(), gtfs_fk("stops.stop_id"), nullable=False),
        sa.Column("to_stop_id", sa.Text(), gtfs_fk("stops.stop_id"), nullable=False),
        sa.Column("transfer_type", sa.SmallInteger(), nullable=False),
        sa.Column("min_transfer_time", sa.Integer()),
        sa.Column("from_trip_id", sa.Text(), gtfs_fk("trips.trip_id")),
        sa.Column("to_trip_id", sa.Text(), gtfs_fk("trips.trip_id")),
        sa.CheckConstraint("transfer_type BETWEEN 0 AND 5", name="transfers_type_check"),
        sa.CheckConstraint("min_transfer_time >= 0", name="transfers_minimum_time_check"),
        schema=GTFS_SCHEMA,
    )
    op.create_index("transfers_from_stop_idx", "transfers", ["from_stop_id"], schema=GTFS_SCHEMA)
    op.create_index("transfers_to_stop_idx", "transfers", ["to_stop_id"], schema=GTFS_SCHEMA)

    op.create_table(
        "attributions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("trip_id", sa.Text(), gtfs_fk("trips.trip_id")),
        sa.Column("organization_name", sa.Text(), nullable=False),
        sa.Column("is_operator", sa.Boolean()),
        schema=GTFS_SCHEMA,
    )
    op.create_index("attributions_trip_idx", "attributions", ["trip_id"], schema=GTFS_SCHEMA)

    for table_name in GTFS_TABLES:
        op.execute(
            sa.text(
                f"CREATE UNLOGGED TABLE {STAGING_SCHEMA}.{table_name} "
                f"AS SELECT * FROM {GTFS_SCHEMA}.{table_name} WITH NO DATA"
            )
        )


def downgrade() -> None:
    op.execute(sa.schema.DropSchema(STAGING_SCHEMA, cascade=True))
    op.execute(sa.schema.DropSchema(GTFS_SCHEMA, cascade=True))
