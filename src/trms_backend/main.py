import os

from fastapi import FastAPI

from trms_backend.api.materials import build_material_router
from trms_backend.api.tasks import build_task_router
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import (
    SqlAlchemyMaterialRepository,
    SqlAlchemyTaskRepository,
)


def create_app(database_url: str | None = None) -> FastAPI:
    app = FastAPI(title="TRMS API")
    session_factory = build_session_factory(
        database_url or os.getenv("DATABASE_URL", "sqlite:///./trms.db")
    )
    init_database(session_factory)
    task_repository = SqlAlchemyTaskRepository(session_factory)
    material_repository = SqlAlchemyMaterialRepository(session_factory)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(build_task_router(task_repository))
    app.include_router(build_material_router(task_repository, material_repository))
    return app


app = create_app()
