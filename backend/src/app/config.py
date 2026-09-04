from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    database_url: str
    gtfs_operator: str = "sl"
    gtfs_regional_static_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GTFS_REGIONAL_STATIC_API_KEY",
            "GTFS-REGIONAL-STATIC-API-KEY",
        ),
    )
    gtfs_cache_dir: Path = Path("/var/lib/gtfs")
    gtfs_validate: bool = True
    gtfs_validator_jar: Path = Path("/opt/gtfs-validator/gtfs-validator-cli.jar")
    gtfs_validator_version: str = "8.0.1"

    @property
    def trafiklab_download_url(self) -> str:
        operator = self.gtfs_operator
        return f"https://opendata.samtrafiken.se/gtfs/{operator}/{operator}.zip"

    @property
    def gtfs_regional_static_api_key_value(self) -> str | None:
        if self.gtfs_regional_static_api_key is None:
            return None
        return self.gtfs_regional_static_api_key.get_secret_value() or None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
