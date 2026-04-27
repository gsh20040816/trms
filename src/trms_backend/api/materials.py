from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from trms_backend.domain.materials import (
    MaterialCreate,
    MaterialRepository,
    MaterialType,
    SubmissionChannel,
)
from trms_backend.domain.tasks import (
    TaskRepository,
    TaskStatus,
    TaskSubmissionDeadlinePassedError,
    TaskSubmitterNotMemberError,
    ensure_task_accepts_member_submission,
)


def build_material_router(
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/tasks/{task_id}/materials", tags=["materials"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    async def submit_materials(
        task_id: str,
        submitter_id: Annotated[str, Form(min_length=1)],
        channel: Annotated[SubmissionChannel, Form()],
        material_type: Annotated[MaterialType, Form()],
        files: Annotated[list[UploadFile], File(min_length=1)],
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        if task.status != TaskStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="task is not open for material submission",
            )
        try:
            ensure_task_accepts_member_submission(task, submitter_id=submitter_id)
        except TaskSubmitterNotMemberError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except TaskSubmissionDeadlinePassedError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        records = []
        for file in files:
            content = await file.read()
            records.append(
                material_repository.create(
                    MaterialCreate(
                        task_id=task_id,
                        submitter_id=submitter_id,
                        channel=channel,
                        material_type=material_type,
                        original_filename=file.filename or "unnamed",
                        content_type=file.content_type,
                        size_bytes=len(content),
                        sha256=sha256(content).hexdigest(),
                    )
                )
            )
        return {"items": records}

    @router.get("")
    def list_materials(task_id: str):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"items": material_repository.list_by_task(task_id)}

    return router
