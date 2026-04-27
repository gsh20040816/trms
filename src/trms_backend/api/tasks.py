from fastapi import APIRouter, HTTPException, status

from trms_backend.domain.global_invoice_config import GlobalInvoiceConfigRepository
from trms_backend.domain.tasks import (
    TaskCreateInput,
    MissingTaskInvoiceConfigError,
    TaskMembersUpdate,
    TaskRepository,
    TaskPublishValidationError,
    TaskStatus,
    TaskStatusUpdate,
    can_transition,
    close_expired_open_tasks,
    ensure_task_can_publish,
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

    @router.get("/{task_id}/members")
    def get_task_members(task_id: str):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"items": task.member_ids}

    @router.put("/{task_id}/members")
    def update_task_members(task_id: str, payload: TaskMembersUpdate):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        if task.status != TaskStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="task members can only be updated while task is draft",
            )
        updated = repository.update_member_ids(task_id, payload.member_ids)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"items": updated.member_ids}

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

        if payload.target_status == TaskStatus.OPEN:
            try:
                ensure_task_can_publish(task)
            except TaskPublishValidationError as error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(error),
                ) from error

        return repository.update_status(task_id, payload.target_status)

    @router.post("/deadline-check")
    def run_task_deadline_check():
        closed_tasks = close_expired_open_tasks(repository)
        return {
            "closed_count": len(closed_tasks),
            "closed_task_ids": [task.id for task in closed_tasks],
        }

    return router
