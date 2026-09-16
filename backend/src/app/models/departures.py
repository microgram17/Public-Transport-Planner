from pydantic import Field

from app.models.gtfs import DatabaseModel

# Separated file for more custom ish models/needs instead of getting from gtfs.db
# and manually reconstructing them with correct fields


class Departure(DatabaseModel):
    stop_id: str
    stop_name: str | None = None
    platform_code: str | None = None

    trip_id: str
    trip_headsign: str | None = None

    route_id: str
    route_short_name: str | None = None
    route_long_name: str | None = None

    arrival_seconds: int | None = Field(default=None, ge=0)
    departure_seconds: int = Field(ge=0)
