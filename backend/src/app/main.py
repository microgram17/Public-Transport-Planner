from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.api.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with db.pool_lifespan():
        yield


app = FastAPI(title="Public Transport Planner API", lifespan=lifespan)
app.include_router(router)
