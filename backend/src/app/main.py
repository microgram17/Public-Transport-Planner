from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, Query

from app import db
from app.config import get_settings
from app.models import Page, Stop


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with db.pool_lifespan():
        yield


app = FastAPI(title="Public Transport Planner API", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config-check")
async def config_check() -> dict[str, bool]:
    return {"database_configured": bool(get_settings().database_url)}


@app.get("/api/stops")
def get_stops(
    connection: Annotated[psycopg.Connection, Depends(db.get_connection)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[Stop]:
    return db.get_stops(connection, limit=limit, offset=offset)
