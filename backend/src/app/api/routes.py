from __future__ import annotations

from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, Query

from app import db
from app.config import get_settings
from app.db.departures import get_departures_for_station
from app.models import Departure, Page, StopSummary

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/config-check")
async def config_check() -> dict[str, bool]:
    return {"database_configured": bool(get_settings().database_url)}


@router.get("/api/stops")
def get_stops(
    connection: Annotated[psycopg.Connection, Depends(db.get_connection)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[StopSummary]:
    return db.get_stops(connection, limit=limit, offset=offset)


# TODO: this needs to have current datetime as an argument in the future, so that we retrieve only data that is relevant for the user

# Placeholder station id until we have an actual selector
SELECTED_STATION_ID = "9021001000193000"


@router.get("/api/departures", response_model=list[Departure])
def get_departures(
    connection: Annotated[psycopg.Connection, Depends(db.get_connection)],
) -> list[Departure]:
    return get_departures_for_station(
        connection,
        station_id=SELECTED_STATION_ID,
    )
