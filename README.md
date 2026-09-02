# Public Transport Planner

Public transport planning application built with React, FastAPI, and PostgreSQL.

## Tech stack

* React + TypeScript + Vite
* FastAPI
* PostgreSQL
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

The default values are configured to use the PostgreSQL container included in the development Compose setup.

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

## Using an external PostgreSQL database

Change `DATABASE_URL` in `.env` to point to the external database:

```env
DATABASE_URL=postgresql://username:password@host:5432/databasename
```

Then start only the frontend and backend:

```bash
docker compose -f compose.dev.yaml up --build --watch backend frontend
```

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
