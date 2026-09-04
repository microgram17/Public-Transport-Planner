# Public Transport Planner

Public transport planning application built with React, FastAPI, and PostgreSQL.

## Tech stack

* React + TypeScript + Vite
* FastAPI
* PostgreSQL 18
* SQLAlchemy 2 + Alembic
* Pydantic Settings
* Docker Compose
* uv

## Quickstart

### Prerequisites

You only need:

* Git
* Docker

### 1. Clone the repository

```bash
git clone https://github.com/microgram17/Public-Transport-Planner
cd Public-Transport-Planner
```

### 2. Create your environment file

Copy the example environment file:

**PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

The default values are configured to use the PostgreSQL container included in the development Compose setup. To
download GTFS data, create a GTFS Regional Static API key in Trafiklab and set `GTFS_REGIONAL_STATIC_API_KEY` in `.env`. Never
commit this key.

### 3. Start the development environment

```bash
docker compose -f compose.dev.yaml up --build --watch
```

This starts:

* Frontend: http://localhost:5173
* Backend: http://localhost:8000
* PostgreSQL: localhost:5432

The backend health endpoint is available at:

```text
http://localhost:8000/health
```

Source changes are automatically synced into the development containers.

Database migrations run before the backend starts. To run them explicitly:

```bash
docker compose -f compose.dev.yaml run --rm migrate
```

## Importing SL GTFS Schedule data

The importer downloads the daily SL archive from Trafiklab, validates it with the pinned MobilityData GTFS validator,
streams it into typed staging tables, checks its references, and transactionally replaces the live `gtfs` tables.

After setting `GTFS_REGIONAL_STATIC_API_KEY` in `.env`, run:

```bash
docker compose -f compose.dev.yaml run --rm --build gtfs-import
```

An archive is skipped by SHA-256 only when its successful import record and the live GTFS dataset are both present. If
the live tables were emptied, the cached archive is imported again automatically. Use `--force` to deliberately reload
an otherwise healthy dataset.

To import the extracted files under `data/sl` without downloading or running the external validator:

```bash
docker compose -f compose.dev.yaml run --rm gtfs-import --file /data/sl --skip-validation
```

The loader supports the GTFS files currently published in the SL feed and the
`samtrafiken_internal_trip_number` extension. Unknown columns are reported and ignored; missing required files or
columns fail the import. Import status, checksums, feed versions, validation reports, and row counts are recorded in
`gtfs.feed_imports`.

GTFS IDs are stored as `text`, dates as `date`, numeric values with numeric PostgreSQL types, and GTFS arrival and
departure times as integer seconds from the start of the service day. This preserves valid times beyond `24:00:00`.

### Database code boundaries

Pydantic validates environment configuration in `backend/src/app/config.py`. SQLAlchemy's typed declarative models in
`backend/src/app/models` are used for normal application queries and as Alembic's autogenerate metadata. The importer
deliberately uses Psycopg `COPY` instead of ORM inserts because GTFS feeds contain millions of rows. The initial Alembic
migration uses structured operations for tables, constraints, and indexes; raw SQL is limited to the PostgreSQL-specific
GTFS time parser and generated constraint-free staging tables.

### Daily production import

Run the same one-shot service from the deployment scheduler after Trafiklab's daily publication window:

```bash
docker compose --env-file .env.production -f compose.prod.yaml run --rm gtfs-import
```

Only one importer can run for an operator at a time; a PostgreSQL advisory lock serializes overlapping jobs.

## Using an external PostgreSQL database

Change `DATABASE_URL` in `.env` to point to the external database:

```env
DATABASE_URL=postgresql://username:password@host:5432/databasename
```

Then start only the frontend and backend:

```bash
docker compose -f compose.dev.yaml up --build --watch backend frontend
```

The database still needs to be reachable by the `migrate` service. For a production deployment, use separate database
roles for migrations, imports, and application queries when the hosting environment supports them.

## Stopping the application

```bash
docker compose -f compose.dev.yaml down
```

The PostgreSQL development volume is preserved between restarts.

To also remove the database volume:

```bash
docker compose -f compose.dev.yaml down -v
```

## Production

The repository also contains production Docker and Compose configurations.

Start the production stack with:

```bash
docker compose --env-file .env.production -f compose.prod.yaml up --build -d
```
