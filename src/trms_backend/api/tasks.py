from fastapi import APIRouter, HTTPException, status

from trms_backend.domain.global_invoice_config import GlobalInvoiceConfigRepository
from trms_backend.domain.tasks import (
    TaskCreateInput,
    MissingTaskInvoiceConfigError,
    TaskRepository,
    TaskStatusUpdate,
    can_transition,
    resolve_task_create,
)


def build_task_router(
    repository: TaskRepository,
    global_invoice_config_repository: GlobalInvoiceConfigRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/tasks", tags=["tasks"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    def create_task(payload: TaskCreateInput):
        try:
            task_create = resolve_task_create(payload, global_invoice_config_repository.get())
        except MissingTaskInvoiceConfigError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        return repository.create(task_create)

    @router.get("")
    def list_tasks():
        return repository.list()

    @router.get("/{task_id}")
    def get_task(task_id: str):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return task

    @router.patch("/{task_id}/status")
    def update_task_status(task_id: str, payload: TaskStatusUpdate):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        if not can_transition(task.status, payload.target_status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"cannot transition task from {task.status} to {payload.target_status}",
            )

        return repository.update_status(task_id, payload.target_status)

    return router
