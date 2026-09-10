from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

import psycopg
from psycopg_pool import ConnectionPool

from app.config import get_settings


@lru_cache
def get_pool() -> ConnectionPool:
    """Create the process-wide pool without opening database connections."""

    settings = get_settings()
    return ConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.database_pool_min_size,
        max_size=settings.database_pool_max_size,
        timeout=settings.database_pool_timeout,
        check=ConnectionPool.check_connection,
        open=False,
    )


@contextmanager
def pool_lifespan() -> Iterator[None]:
    """Open the pool for the application lifespan and close it on shutdown."""

    pool = get_pool()
    try:
        pool.open(wait=True, timeout=get_settings().database_pool_timeout)
        yield
    finally:
        pool.close()
        get_pool.cache_clear()


def get_connection() -> Iterator[psycopg.Connection]:
    """Provide one pooled Psycopg connection per FastAPI request."""

    with get_pool().connection() as connection:
        yield connection
