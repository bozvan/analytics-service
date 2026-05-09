from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import initialize_database
from app.routers.analytics import router as analytics_router
from app.routers.internal import router as internal_router
from app.routers.users import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Analytics Service",
        description="Analytics, internal events, and achievements for surveys.",
        version="1.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", summary="Service healthcheck")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(analytics_router)
    app.include_router(internal_router)
    app.include_router(users_router)
    return app


app = create_app()
