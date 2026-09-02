import os

from fastapi import FastAPI

app = FastAPI(title="Train Tracking API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config-check")
async def config_check() -> dict[str, str]:
    database_url = os.getenv("DATABASE_URL", "")
    return {"database_configured": str(bool(database_url))}
