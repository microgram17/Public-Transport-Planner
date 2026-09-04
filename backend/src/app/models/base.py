from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for application-owned SQLAlchemy models."""

    metadata = MetaData(schema="gtfs")
