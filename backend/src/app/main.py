import os

from fastapi import FastAPI

app = FastAPI(title="Public Transport Planner API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config-check")
async def config_check() -> dict[str, str]:
    database_url = os.getenv("DATABASE_URL", "")
    return {"database_configured": str(bool(database_url))}
