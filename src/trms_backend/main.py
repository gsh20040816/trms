from fastapi import FastAPI

from trms_backend.api.tasks import build_task_router
from trms_backend.domain.tasks import InMemoryTaskRepository


def create_app() -> FastAPI:
    app = FastAPI(title="TRMS API")
    task_repository = InMemoryTaskRepository()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(build_task_router(task_repository))
    return app


app = create_app()

