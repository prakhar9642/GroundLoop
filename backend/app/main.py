"""FastAPI application factory for GroundLoop."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from .database import Database
from .routers.messages import router as messages_router
from .service import GroundLoopService


def create_app(db_path: str | Path | None = None) -> FastAPI:
    if db_path is None:
        configured_path = os.environ.get("GROUNDLOOP_DB_PATH")
        db_path = configured_path or Path(__file__).resolve().parents[1] / "data" / "groundloop.db"

    database = Database(db_path)
    app = FastAPI(title="GroundLoop API", version="0.1.0")
    app.state.database = database
    app.state.service = GroundLoopService(database)
    app.include_router(messages_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"service": "GroundLoop", "status": "ok"}

    return app


app = create_app()
