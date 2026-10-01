#!/bin/sh
set -eu

extract_file="${OSM_EXTRACT_FILE:-/data/gtfs-area.osm.pbf}"
padding_degrees="${OSM_BBOX_PADDING_DEGREES:-0.25}"
cache_mb="${OSM_CACHE_MB:-800}"
osm_schema="${OSM_SCHEMA:-osm}"

fail() {
    printf 'OSM import error: %s\n' "$1" >&2
    exit 1
}

source_file="${OSM_SOURCE_FILE:-}"

if [ -z "$source_file" ]; then
    for candidate in /data/*.osm.pbf; do
        [ -f "$candidate" ] || continue
        [ "$candidate" = "$extract_file" ] && continue

        if [ -n "$source_file" ]; then
            fail "multiple source PBF files found in /data; set OSM_SOURCE_FILE in .env"
        fi

        source_file="$candidate"
    done
fi

[ -n "$source_file" ] || fail "no source .osm.pbf found in /data"
[ -f "$source_file" ] || fail "source PBF does not exist: $source_file"
[ "$source_file" != "$extract_file" ] || fail "OSM_SOURCE_FILE and OSM_EXTRACT_FILE must differ"

printf 'Reading GTFS stop bounds from %s...\n' "${PGDATABASE:-the configured database}"

gtfs_bounds="$(
    psql \
        --set=ON_ERROR_STOP=1 \
        --set=padding="$padding_degrees" \
        --no-align \
        --tuples-only <<'SQL'
WITH bounds AS (
    SELECT
        min(stop_lon::double precision) AS min_lon,
        min(stop_lat::double precision) AS min_lat,
        max(stop_lon::double precision) AS max_lon,
        max(stop_lat::double precision) AS max_lat
    FROM gtfs.stops
    WHERE stop_lon::double precision BETWEEN -180 AND 180
      AND stop_lat::double precision BETWEEN -90 AND 90
)
SELECT concat_ws(
    ',',
    min_lon - :'padding'::double precision,
    min_lat - :'padding'::double precision,
    max_lon + :'padding'::double precision,
    max_lat + :'padding'::double precision
)
FROM bounds
WHERE min_lon IS NOT NULL;
SQL
)"

[ -n "$gtfs_bounds" ] || fail "gtfs.stops has no valid longitude/latitude coordinates"

printf 'Source PBF: %s\n' "$source_file"
printf 'Prepared PBF: %s\n' "$extract_file"
printf 'Extraction bbox (min lon,min lat,max lon,max lat): %s\n' "$gtfs_bounds"
printf 'Completing all boundary and multipolygon relations that touch the bbox...\n'

osmium extract \
    --strategy=smart \
    --option=types=multipolygon,boundary \
    --bbox="$gtfs_bounds" \
    --set-bounds \
    --overwrite \
    --output="$extract_file" \
    "$source_file"

printf 'Checking that every extracted way has all referenced nodes...\n'
osmium check-refs "$extract_file"

printf 'Replacing the osm2pgsql tables in schema %s...\n' "$osm_schema"
osm2pgsql \
    --create \
    --slim \
    --drop \
    --schema="$osm_schema" \
    --cache="$cache_mb" \
    "$extract_file"

printf 'Refreshing administrative boundaries and materialized GTFS display names...\n'
psql \
    --set=ON_ERROR_STOP=1 \
    --command='SELECT osm.refresh_admin_boundaries(); REFRESH MATERIALIZED VIEW gtfs.stops_with_display_name;'

printf 'OSM import completed successfully.\n'
