from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from trms_backend.domain.exports import (
    TaskExportActorNotAllowedError,
    TaskExportFormatNotSupportedError,
    TaskExportJobNotReadyError,
    TaskExportJobRepository,
    TaskExportJobRequest,
    TaskExportJobStatusTransitionError,
    TaskExportJobStatusUpdate,
    build_task_export_boundary,
    create_task_export_job,
    list_task_export_jobs,
    update_task_export_job_status,
)
from trms_backend.domain.tasks import TaskRepository


def build_export_router(
    task_repository: TaskRepository,
    export_job_repository: TaskExportJobRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/tasks", tags=["exports"])

    @router.get("/{task_id}/exports/capabilities")
    def get_task_export_capabilities(
        task_id: str,
        actor_id: Annotated[str, Query(min_length=1)],
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        try:
            return build_task_export_boundary(task, actor_id=actor_id)
        except TaskExportActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.post("/{task_id}/exports", status_code=status.HTTP_201_CREATED)
    def create_export_job(task_id: str, payload: TaskExportJobRequest):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        try:
            return create_task_export_job(
                task,
                payload=payload,
                repository=export_job_repository,
            )
        except TaskExportActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except TaskExportJobNotReadyError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except TaskExportFormatNotSupportedError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/exports")
    def list_export_jobs(
        task_id: str,
        actor_id: Annotated[str, Query(min_length=1)],
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        try:
            return list_task_export_jobs(
                task,
                actor_id=actor_id,
                repository=export_job_repository,
            )
        except TaskExportActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.patch("/exports/{export_job_id}/status")
    def update_export_job_status(export_job_id: str, payload: TaskExportJobStatusUpdate):
        export_job = export_job_repository.get(export_job_id)
        if export_job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="export job not found",
            )

        task = task_repository.get(export_job.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        try:
            return update_task_export_job_status(
                task,
                export_job=export_job,
                payload=payload,
                repository=export_job_repository,
            )
        except TaskExportActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except TaskExportJobStatusTransitionError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

    return router
