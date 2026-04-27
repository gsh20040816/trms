from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from trms_backend.domain.exports import (
    TaskExportActorNotAllowedError,
    build_task_export_boundary,
)
from trms_backend.domain.tasks import TaskRepository


def build_export_router(repository: TaskRepository) -> APIRouter:
    router = APIRouter(prefix="/api/tasks", tags=["exports"])

    @router.get("/{task_id}/exports/capabilities")
    def get_task_export_capabilities(
        task_id: str,
        actor_id: Annotated[str, Query(min_length=1)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        try:
            return build_task_export_boundary(task, actor_id=actor_id)
        except TaskExportActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    return router
