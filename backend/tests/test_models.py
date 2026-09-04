from sqlalchemy import Double, Integer
from sqlalchemy.orm import configure_mappers

from app.gtfs.manifest import TABLES
from app.models import Base, StopTime


def test_gtfs_models_cover_imported_tables() -> None:
    expected = {table.name for table in TABLES} | {"feed_imports"}

    assert set(Base.metadata.tables) == {f"gtfs.{name}" for name in expected}


def test_models_use_database_types_for_gtfs_values() -> None:
    configure_mappers()

    assert isinstance(StopTime.__table__.c.arrival_seconds.type, Integer)
    assert isinstance(Base.metadata.tables["gtfs.stops"].c.stop_lat.type, Double)
    assert StopTime.__table__.primary_key.columns.keys() == ["trip_id", "stop_sequence"]


def test_feed_import_index_keeps_newest_imports_first() -> None:
    index = next(
        index
        for index in Base.metadata.tables["gtfs.feed_imports"].indexes
        if index.name == "feed_imports_operator_imported_idx"
    )

    assert str(index.expressions[1]).endswith("imported_at DESC")
