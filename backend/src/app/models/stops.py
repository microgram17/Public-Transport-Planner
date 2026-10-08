from pydantic import BaseModel


class StopSummary(BaseModel):
    stop_id: str
    display_name: str | None = None
    location_type: int
