from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    database_url: str
    database_pool_min_size: int = Field(default=1, ge=0)
    database_pool_max_size: int = Field(default=10, ge=1)
    database_pool_timeout: float = Field(default=30.0, gt=0)
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

    @model_validator(mode="after")
    def validate_database_pool_size(self) -> Settings:
        if self.database_pool_min_size > self.database_pool_max_size:
            raise ValueError("DATABASE_POOL_MIN_SIZE cannot exceed DATABASE_POOL_MAX_SIZE")
        return self

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
