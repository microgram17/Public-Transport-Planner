\set ON_ERROR_STOP on
\pset pager off

\echo '== Database, PostGIS, and search path =='
SELECT current_database() AS database,
       current_user AS database_user,
       current_setting('server_version') AS postgres_version,
       current_setting('search_path') AS search_path;

SELECT e.extname,
       e.extversion,
       n.nspname AS extension_schema
FROM pg_catalog.pg_extension AS e
JOIN pg_catalog.pg_namespace AS n ON n.oid = e.extnamespace
WHERE e.extname = 'postgis';

SELECT public.postgis_full_version();

SELECT to_regprocedure('postgis_full_version()') AS unqualified_postgis_function,
       to_regclass('geometry_columns') AS unqualified_geometry_columns,
       to_regclass('public.geometry_columns') AS public_geometry_columns;

SELECT COALESCE(d.datname, 'all databases') AS database,
       COALESCE(r.rolname, 'all roles') AS role,
       settings.setconfig
FROM pg_catalog.pg_db_role_setting AS settings
LEFT JOIN pg_catalog.pg_database AS d ON d.oid = settings.setdatabase
LEFT JOIN pg_catalog.pg_roles AS r ON r.oid = settings.setrole
WHERE settings.setdatabase IN (
    0,
    (SELECT oid FROM pg_catalog.pg_database WHERE datname = current_database())
)
ORDER BY database, role;

\echo '== GTFS stops =='
SELECT column_name,
       data_type,
       udt_schema,
       udt_name,
       is_nullable
FROM information_schema.columns
WHERE table_schema = 'gtfs'
  AND table_name = 'stops'
  AND column_name IN ('stop_id', 'stop_name', 'stop_lat', 'stop_lon')
ORDER BY ordinal_position;

SELECT count(*) AS stop_count,
       count(*) FILTER (WHERE stop_lat IS NULL OR stop_lon IS NULL) AS null_coordinates,
       count(*) FILTER (
           WHERE stop_lat NOT BETWEEN -90 AND 90
              OR stop_lon NOT BETWEEN -180 AND 180
       ) AS invalid_coordinates,
       min(stop_lat) AS min_lat,
       max(stop_lat) AS max_lat,
       min(stop_lon) AS min_lon,
       max(stop_lon) AS max_lon
FROM gtfs.stops;

\echo '== OSM import metadata and geometry columns =='
SELECT property, value
FROM osm.osm2pgsql_properties
ORDER BY property;

SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'osm'
ORDER BY table_name;

SELECT table_name,
       column_name,
       data_type,
       udt_schema,
       udt_name
FROM information_schema.columns
WHERE table_schema = 'osm'
  AND column_name IN (
      'osm_id',
      'name',
      'place',
      'boundary',
      'admin_level',
      'way'
  )
ORDER BY table_name, ordinal_position;

SELECT f_table_schema,
       f_table_name,
       f_geometry_column,
       coord_dimension,
       srid,
       type
FROM public.geometry_columns
WHERE f_table_schema = 'osm'
ORDER BY f_table_name;

SELECT 'line' AS osm_table,
       count(*) AS row_count,
       count(*) FILTER (WHERE way IS NULL) AS null_geometries,
       count(*) FILTER (WHERE public.ST_IsEmpty(way)) AS empty_geometries,
       count(*) FILTER (WHERE NOT public.ST_IsValid(way)) AS invalid_geometries,
       min(public.ST_SRID(way)) AS min_srid,
       max(public.ST_SRID(way)) AS max_srid
FROM osm.planet_osm_line
UNION ALL
SELECT 'point', count(*),
       count(*) FILTER (WHERE way IS NULL),
       count(*) FILTER (WHERE public.ST_IsEmpty(way)),
       count(*) FILTER (WHERE NOT public.ST_IsValid(way)),
       min(public.ST_SRID(way)), max(public.ST_SRID(way))
FROM osm.planet_osm_point
UNION ALL
SELECT 'polygon', count(*),
       count(*) FILTER (WHERE way IS NULL),
       count(*) FILTER (WHERE public.ST_IsEmpty(way)),
       count(*) FILTER (WHERE NOT public.ST_IsValid(way)),
       min(public.ST_SRID(way)), max(public.ST_SRID(way))
FROM osm.planet_osm_polygon
UNION ALL
SELECT 'roads', count(*),
       count(*) FILTER (WHERE way IS NULL),
       count(*) FILTER (WHERE public.ST_IsEmpty(way)),
       count(*) FILTER (WHERE NOT public.ST_IsValid(way)),
       min(public.ST_SRID(way)), max(public.ST_SRID(way))
FROM osm.planet_osm_roads
ORDER BY osm_table;

WITH bounds AS (
    SELECT 'line' AS osm_table,
           public.ST_Extent(public.ST_Transform(way, 4326))::public.box2d AS box
    FROM osm.planet_osm_line
    UNION ALL
    SELECT 'point', public.ST_Extent(public.ST_Transform(way, 4326))::public.box2d
    FROM osm.planet_osm_point
    UNION ALL
    SELECT 'polygon', public.ST_Extent(public.ST_Transform(way, 4326))::public.box2d
    FROM osm.planet_osm_polygon
    UNION ALL
    SELECT 'roads', public.ST_Extent(public.ST_Transform(way, 4326))::public.box2d
    FROM osm.planet_osm_roads
)
SELECT osm_table,
       public.ST_XMin(box) AS min_lon,
       public.ST_YMin(box) AS min_lat,
       public.ST_XMax(box) AS max_lon,
       public.ST_YMax(box) AS max_lat
FROM bounds
ORDER BY osm_table;

\echo '== Relevant OSM tags =='
SELECT 'point place' AS category,
       count(*) AS row_count,
       count(*) FILTER (WHERE name IS NOT NULL) AS named_count
FROM osm.planet_osm_point
WHERE place IS NOT NULL
UNION ALL
SELECT 'polygon place', count(*), count(*) FILTER (WHERE name IS NOT NULL)
FROM osm.planet_osm_polygon
WHERE place IS NOT NULL
UNION ALL
SELECT 'polygon boundary', count(*), count(*) FILTER (WHERE name IS NOT NULL)
FROM osm.planet_osm_polygon
WHERE boundary IS NOT NULL
UNION ALL
SELECT 'line boundary', count(*), count(*) FILTER (WHERE name IS NOT NULL)
FROM osm.planet_osm_line
WHERE boundary IS NOT NULL
UNION ALL
SELECT 'polygon admin_level', count(*), count(*) FILTER (WHERE name IS NOT NULL)
FROM osm.planet_osm_polygon
WHERE admin_level IS NOT NULL
UNION ALL
SELECT 'line admin_level', count(*), count(*) FILTER (WHERE name IS NOT NULL)
FROM osm.planet_osm_line
WHERE admin_level IS NOT NULL
ORDER BY category;

\echo '== Test stop 9021001022041000 =='
WITH test_stop AS (
    SELECT stop_id,
           stop_name,
           stop_lat,
           stop_lon,
           public.ST_SetSRID(public.ST_MakePoint(stop_lon, stop_lat), 4326) AS point_4326
    FROM gtfs.stops
    WHERE stop_id = '9021001022041000'
)
SELECT stop_id,
       stop_name,
       stop_lat,
       stop_lon,
       public.ST_AsText(point_4326) AS point_wkt,
       public.ST_SRID(point_4326) AS source_srid,
       public.ST_SRID(public.ST_Transform(point_4326, 3857)) AS osm_srid,
       stop_lon BETWEEN 17.95 AND 18.20
           AND stop_lat BETWEEN 59.25 AND 59.40 AS inside_requested_bbox
FROM test_stop;

WITH test_stop AS (
    SELECT public.ST_SetSRID(
               public.ST_MakePoint(stop_lon, stop_lat),
               4326
           ) AS point_4326
    FROM gtfs.stops
    WHERE stop_id = '9021001022041000'
),
osm_bounds AS (
    SELECT public.ST_SetSRID(
               public.ST_Extent(public.ST_Transform(way, 4326))::public.geometry,
               4326
           ) AS geometry
    FROM osm.planet_osm_point
)
SELECT public.ST_Covers(osm_bounds.geometry, test_stop.point_4326)
           AS inside_imported_osm_extent
FROM test_stop
CROSS JOIN osm_bounds;

\echo 'Nearby place points (true geodesic distance, 5 km)'
WITH test_stop AS (
    SELECT public.ST_SetSRID(
               public.ST_MakePoint(stop_lon, stop_lat),
               4326
           )::public.geography AS geog
    FROM gtfs.stops
    WHERE stop_id = '9021001022041000'
)
SELECT osm.osm_id,
       osm.name,
       osm.place,
       round(public.ST_Distance(
           public.ST_Transform(osm.way, 4326)::public.geography,
           test_stop.geog
       )) AS distance_m
FROM osm.planet_osm_point AS osm
CROSS JOIN test_stop
WHERE osm.place IS NOT NULL
  AND public.ST_DWithin(
      public.ST_Transform(osm.way, 4326)::public.geography,
      test_stop.geog,
      5000
  )
ORDER BY public.ST_Distance(
             public.ST_Transform(osm.way, 4326)::public.geography,
             test_stop.geog
         ),
         osm.name
LIMIT 20;

\echo 'Containing OSM polygons (zero rows is valid when no mapped polygon covers the stop)'
WITH test_stop AS (
    SELECT public.ST_Transform(
               public.ST_SetSRID(public.ST_MakePoint(stop_lon, stop_lat), 4326),
               3857
           ) AS point_3857
    FROM gtfs.stops
    WHERE stop_id = '9021001022041000'
)
SELECT osm.osm_id,
       osm.name,
       osm.place,
       osm.boundary,
       osm.admin_level,
       osm.building,
       osm.landuse,
       public.ST_GeometryType(osm.way) AS geometry_type
FROM osm.planet_osm_polygon AS osm
CROSS JOIN test_stop
WHERE public.ST_Covers(osm.way, test_stop.point_3857)
ORDER BY (osm.boundary IS NOT NULL OR osm.admin_level IS NOT NULL) DESC,
         (osm.place IS NOT NULL) DESC,
         osm.name NULLS LAST;

\echo 'Administrative boundary evidence near the test stop'
SELECT osm_id,
       name,
       boundary,
       admin_level,
       public.ST_IsClosed(way) AS is_closed,
       public.ST_AsText(
           public.ST_Envelope(public.ST_Transform(way, 4326))
       ) AS bounds
FROM osm.planet_osm_line
WHERE osm_id = -398035
ORDER BY osm_id;
