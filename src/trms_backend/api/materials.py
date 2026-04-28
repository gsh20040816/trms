from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from trms_backend.api.material_submission_http import build_batch_response, read_uploaded_files
from trms_backend.api.request_identity import (
    RequestIdentity,
    build_optional_request_identity_dependency,
)
from trms_backend.api.request_identity_http import resolve_required_actor_request_field
from trms_backend.api.request_task_access import TaskAccessScope, resolve_task_access_scope
from trms_backend.application.material_submission import (
    MaterialSubmissionService,
    MaterialSubmissionTaskNotFoundError,
    MaterialSubmissionTaskNotOpenError,
)
from trms_backend.domain.auth import AuthRepository
from trms_backend.domain.materials import (
    MaterialStatus,
    MaterialRepository,
    MaterialType,
    SubmissionChannel,
)
from trms_backend.domain.tasks import (
    TaskRepository,
    TaskSubmissionDeadlinePassedError,
    TaskSubmitterNotMemberError,
    ensure_task_has_member,
)


def build_material_router(
    auth_repository: AuthRepository,
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    material_submission_service: MaterialSubmissionService,
) -> APIRouter:
    router = APIRouter(tags=["materials"])
    optional_request_identity = build_optional_request_identity_dependency(auth_repository)

    @router.post("/api/tasks/{task_id}/materials", status_code=status.HTTP_201_CREATED)
    async def submit_materials(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
        channel: Annotated[SubmissionChannel, Form()],
        material_type: Annotated[MaterialType, Form()],
        files: Annotated[list[UploadFile], File(min_length=1)],
        submitter_id: Annotated[str | None, Form(min_length=1)] = None,
    ):
        uploaded_files = await read_uploaded_files(files)
        resolved_submitter_id = resolve_required_actor_request_field(
            identity,
            submitter_id,
            field_name="submitter_id",
        )
        try:
            result = material_submission_service.submit_to_task(
                task_id=task_id,
                submitter_id=resolved_submitter_id,
                channel=channel,
                material_type=material_type,
                files=uploaded_files,
            )
        except MaterialSubmissionTaskNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        except MaterialSubmissionTaskNotOpenError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="task is not open for material submission",
            )
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

        return build_batch_response(result, file_count=len(uploaded_files))

    @router.post("/api/materials/pending-assignment", status_code=status.HTTP_201_CREATED)
    async def submit_pending_assignment_materials(
        channel: Annotated[SubmissionChannel, Form()],
        material_type: Annotated[MaterialType, Form()],
        files: Annotated[list[UploadFile], File(min_length=1)],
        task_id_hint: Annotated[str | None, Form()] = None,
        submitter_id_hint: Annotated[str | None, Form()] = None,
    ):
        uploaded_files = await read_uploaded_files(files)
        result = material_submission_service.submit_pending_assignment(
            channel=channel,
            material_type=material_type,
            files=uploaded_files,
            task_id_hint=task_id_hint,
            submitter_id_hint=submitter_id_hint,
        )
        return build_batch_response(result, file_count=len(uploaded_files))

    @router.post("/api/materials/{material_id}/claim")
    def claim_pending_assignment_material(
        material_id: str,
        administrator_id: Annotated[str, Form(min_length=1)],
        task_id: Annotated[str, Form(min_length=1)],
        submitter_id: Annotated[str, Form(min_length=1)],
    ):
        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")
        if material.status is not MaterialStatus.PENDING_ASSIGNMENT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="material is not pending assignment",
            )

        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        if task.administrator_id != administrator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="administrator is not allowed to claim materials for this task",
            )

        try:
            ensure_task_has_member(task, submitter_id=submitter_id)
        except TaskSubmitterNotMemberError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        claimed_material = material_repository.claim_pending_assignment(
            material_id=material_id,
            task_id=task_id,
            submitter_id=submitter_id,
            claimed_by=administrator_id,
        )
        if claimed_material is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="material is not pending assignment",
            )
        return {"item": claimed_material}

    @router.get("/api/tasks/{task_id}/materials")
    def list_materials(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        items = material_repository.list_by_task(task_id)
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to view materials for this task",
        )
        if scope is TaskAccessScope.MEMBER:
            actor_id = identity.actor_id or ""
            items = [item for item in items if item.submitter_id == actor_id]
        return {"items": items}

    return router
