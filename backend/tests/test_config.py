from pathlib import Path

import pytest

from app.config import Settings


def test_trafiklab_url_does_not_contain_api_key(tmp_path: Path) -> None:
    settings = Settings(
        database_url="postgresql://example",
        gtfs_regional_static_api_key="secret-value",
        gtfs_operator="sl",
        gtfs_cache_dir=tmp_path,
    )

    assert settings.trafiklab_download_url == "https://opendata.samtrafiken.se/gtfs/sl/sl.zip"
    assert "secret-value" not in settings.trafiklab_download_url


@pytest.mark.parametrize(
    "variable_name",
    ["GTFS_REGIONAL_STATIC_API_KEY", "GTFS-REGIONAL-STATIC-API-KEY"],
)
def test_accepts_current_and_legacy_api_key_environment_names(
    monkeypatch: pytest.MonkeyPatch,
    variable_name: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv(variable_name, "secret-value")

    settings = Settings(_env_file=None)

    assert settings.gtfs_regional_static_api_key_value == "secret-value"


def test_rejects_inverted_database_pool_sizes() -> None:
    with pytest.raises(ValueError, match="DATABASE_POOL_MIN_SIZE"):
        Settings(
            database_url="postgresql://example",
            database_pool_min_size=5,
            database_pool_max_size=2,
        )
