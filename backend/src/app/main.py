from fastapi import FastAPI

from app.config import get_settings

app = FastAPI(title="Public Transport Planner API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config-check")
async def config_check() -> dict[str, bool]:
    return {"database_configured": bool(get_settings().database_url)}
