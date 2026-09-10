from types import NoneType
from typing import get_args

import pytest
from pydantic import ValidationError

from app.gtfs.manifest import TABLES
from app.models import GTFS_MODELS, FeedImport, Page, Stop


def test_gtfs_models_cover_imported_tables() -> None:
    assert set(GTFS_MODELS) == {table.name for table in TABLES}


def test_gtfs_model_fields_cover_database_rows() -> None:
    generated_fields = {
        "attributions": {"id"},
        "transfers": {"id"},
    }

    for table in TABLES:
        expected = {field.target for field in table.fields} | generated_fields.get(table.name, set())
        assert set(GTFS_MODELS[table.name].model_fields) == expected


def test_optional_model_fields_default_to_none() -> None:
    for model in [FeedImport, *GTFS_MODELS.values()]:
        for field in model.model_fields.values():
            if NoneType in get_args(field.annotation):
                assert not field.is_required()
                assert field.default is None


def test_stop_validates_database_constraints() -> None:
    with pytest.raises(ValidationError):
        Stop(
            stop_id="invalid",
            stop_name="Invalid stop",
            stop_lat=91,
            stop_lon=18,
            location_type=0,
            parent_station=None,
            platform_code=None,
        )


def test_page_preserves_its_item_type() -> None:
    page = Page[Stop](items=[{"stop_id": "stop-a"}], total=1, limit=10, offset=0)

    assert isinstance(page.items[0], Stop)
