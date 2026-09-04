from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

import psycopg
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def connect() -> psycopg.Connection:
    """Open a Psycopg connection for COPY-heavy import operations."""

    return psycopg.connect(get_settings().database_url)


def sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


@lru_cache
def get_engine() -> Engine:
    return create_engine(sqlalchemy_url(get_settings().database_url), pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency for ordinary application queries."""

    with get_session_factory()() as session:
        yield session
