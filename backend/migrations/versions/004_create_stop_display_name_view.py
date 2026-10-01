"""Create stable OSM boundary context and the GTFS stop display-name view.

Revision ID: 004
Revises: 003
"""

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


ADMIN_BOUNDARIES_TABLE = r"""
CREATE TABLE osm.admin_boundaries (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    osm_id bigint NOT NULL,
    name text NOT NULL,
    admin_level smallint NOT NULL,
    way public.geometry(Geometry, 3857) NOT NULL
);

CREATE INDEX admin_boundaries_osm_id_idx
    ON osm.admin_boundaries (osm_id);

CREATE INDEX admin_boundaries_level_idx
    ON osm.admin_boundaries (admin_level);

CREATE INDEX admin_boundaries_way_idx
    ON osm.admin_boundaries USING gist (way);
"""


REFRESH_FUNCTION = r"""
CREATE FUNCTION osm.refresh_admin_boundaries()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    IF to_regclass('osm.planet_osm_polygon') IS NULL THEN
        RAISE EXCEPTION 'osm.planet_osm_polygon does not exist; import OSM data first';
    END IF;

    TRUNCATE osm.admin_boundaries RESTART IDENTITY;

    EXECUTE $insert$
        INSERT INTO osm.admin_boundaries (osm_id, name, admin_level, way)
        SELECT
            osm_id,
            name,
            admin_level::smallint,
            way
        FROM osm.planet_osm_polygon
        WHERE boundary = 'administrative'
          AND name IS NOT NULL
          AND admin_level ~ '^[0-9]+$'
          AND NOT ST_IsEmpty(way)
          AND ST_IsValid(way)
    $insert$;
END;
$$;
"""


STOP_DISPLAY_NAME_VIEW = r"""
CREATE MATERIALIZED VIEW gtfs.stops_with_display_name AS
WITH stop_anchors AS (
    SELECT
        stop_id,
        COALESCE(parent_station, stop_id) AS anchor_stop_id
    FROM gtfs.stops
),
anchors AS (
    SELECT
        anchor.stop_id AS anchor_stop_id,
        anchor.stop_name AS anchor_stop_name,
        COALESCE(lower(btrim(anchor.stop_name)), 'stop:' || anchor.stop_id) AS name_key,
        CASE
            WHEN anchor.stop_lon IS NOT NULL AND anchor.stop_lat IS NOT NULL
            THEN ST_SetSRID(ST_MakePoint(anchor.stop_lon, anchor.stop_lat), 4326)
        END AS point_4326
    FROM (
        SELECT DISTINCT anchor_stop_id
        FROM stop_anchors
    ) AS anchor_ids
    JOIN gtfs.stops AS anchor
      ON anchor.stop_id = anchor_ids.anchor_stop_id
),
projected_anchors AS (
    SELECT
        anchors.*,
        ST_Transform(point_4326, 3006) AS point_3006,
        ST_Transform(point_4326, 3857) AS point_3857
    FROM anchors
),
clustered_anchors AS (
    SELECT
        projected_anchors.*,
        ST_ClusterDBSCAN(point_3006, eps => 500, minpoints => 1)
            OVER (PARTITION BY name_key) AS cluster_number
    FROM projected_anchors
),
located_anchors AS (
    SELECT
        anchor_stop_id,
        anchor_stop_name,
        name_key,
        COALESCE(cluster_number::text, 'stop:' || anchor_stop_id) AS cluster_key,
        regexp_replace(municipality.name, '[[:space:]]+kommun$', '', 'i') AS municipality_name,
        county.name AS county_name
    FROM clustered_anchors AS anchor
    LEFT JOIN LATERAL (
        SELECT boundary.name
        FROM osm.admin_boundaries AS boundary
        WHERE boundary.admin_level = 7
          AND boundary.way && anchor.point_3857
          AND ST_Covers(boundary.way, anchor.point_3857)
        ORDER BY ST_Area(boundary.way), boundary.osm_id
        LIMIT 1
    ) AS municipality ON true
    LEFT JOIN LATERAL (
        SELECT boundary.name
        FROM osm.admin_boundaries AS boundary
        WHERE boundary.admin_level = 4
          AND boundary.way && anchor.point_3857
          AND ST_Covers(boundary.way, anchor.point_3857)
        ORDER BY ST_Area(boundary.way), boundary.osm_id
        LIMIT 1
    ) AS county ON true
),
location_context AS (
    SELECT
        name_key,
        cluster_key,
        min(municipality_name) AS municipality_name,
        min(county_name) AS county_name
    FROM located_anchors
    GROUP BY name_key, cluster_key
),
counted_locations AS (
    SELECT
        location_context.*,
        count(*) OVER (PARTITION BY name_key) AS name_location_count,
        count(*) OVER (PARTITION BY name_key, municipality_name) AS municipality_location_count
    FROM location_context
),
anchor_context AS (
    SELECT
        anchor.anchor_stop_id,
        context.municipality_name,
        context.county_name,
        context.name_location_count,
        context.municipality_location_count
    FROM located_anchors AS anchor
    JOIN counted_locations AS context
      ON context.name_key = anchor.name_key
     AND context.cluster_key = anchor.cluster_key
)
SELECT
    stop.*,
    context.municipality_name,
    context.county_name,
    CASE
        WHEN context.name_location_count > 1 THEN context.municipality_name
    END AS disambiguation_name,
    CASE
        WHEN context.name_location_count > 1
         AND context.municipality_name IS NOT NULL
        THEN stop.stop_name || ' (' || context.municipality_name || ')'
        ELSE stop.stop_name
    END AS display_name,
    CASE
        WHEN context.name_location_count > 1
        THEN context.municipality_name IS NULL
          OR context.municipality_location_count > 1
        ELSE false
    END AS needs_secondary_disambiguation
FROM gtfs.stops AS stop
JOIN stop_anchors AS stop_anchor
  ON stop_anchor.stop_id = stop.stop_id
JOIN anchor_context AS context
  ON context.anchor_stop_id = stop_anchor.anchor_stop_id;

CREATE UNIQUE INDEX stops_with_display_name_stop_id_idx
    ON gtfs.stops_with_display_name (stop_id);

CREATE INDEX stops_with_display_name_name_parent_idx
    ON gtfs.stops_with_display_name (stop_name, parent_station);

CREATE INDEX stops_with_display_name_display_name_idx
    ON gtfs.stops_with_display_name (display_name);

COMMENT ON MATERIALIZED VIEW gtfs.stops_with_display_name IS
    'GTFS stops with OSM municipality/county context and user-facing duplicate-name disambiguation.';

COMMENT ON COLUMN gtfs.stops_with_display_name.disambiguation_name IS
    'Municipality suffix used when the stop name occurs in multiple geographic clusters.';

COMMENT ON COLUMN gtfs.stops_with_display_name.needs_secondary_disambiguation IS
    'True when municipality alone does not distinguish all geographic clusters with this stop name.';
"""


def upgrade() -> None:
    op.execute(ADMIN_BOUNDARIES_TABLE)
    op.execute(REFRESH_FUNCTION)
    op.execute(
        r"""
        DO $$
        BEGIN
            IF to_regclass('osm.planet_osm_polygon') IS NOT NULL THEN
                PERFORM osm.refresh_admin_boundaries();
            END IF;
        END
        $$
        """
    )
    op.execute(STOP_DISPLAY_NAME_VIEW)


def downgrade() -> None:
    op.execute(
        r"""
        DO $$
        DECLARE
            relation_kind "char";
        BEGIN
            SELECT relkind
            INTO relation_kind
            FROM pg_class
            WHERE oid = to_regclass('gtfs.stops_with_display_name');

            IF relation_kind = 'm' THEN
                DROP MATERIALIZED VIEW gtfs.stops_with_display_name;
            ELSIF relation_kind = 'v' THEN
                DROP VIEW gtfs.stops_with_display_name;
            END IF;
        END
        $$
        """
    )
    op.execute("DROP FUNCTION IF EXISTS osm.refresh_admin_boundaries()")
    op.execute("DROP TABLE IF EXISTS osm.admin_boundaries")
