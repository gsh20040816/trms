from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from trms_backend.api.error_responses import ensure_request_id
from trms_backend.api.material_submission_http import build_batch_response, read_uploaded_files
from trms_backend.api.request_identity import (
    RequestIdentity,
    build_authenticated_request_identity_dependency,
    build_optional_request_identity_dependency,
)
from trms_backend.api.request_identity_http import resolve_required_actor_request_field
from trms_backend.api.request_task_access import TaskAccessScope, resolve_task_access_scope
from trms_backend.application.material_deletion import (
    MaterialDeletionActorNotAllowedError,
    MaterialDeletionConflictError,
    MaterialDeletionNotFoundError,
    MaterialDeletionService,
    MaterialDeletionTaskNotFoundError,
)
from trms_backend.application.material_submission import (
    MaterialSubmissionService,
    MaterialSubmissionTaskNotFoundError,
    MaterialSubmissionTaskNotOpenError,
)
from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
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


class MaterialDeletionMarkRequest(BaseModel):
    administrator_id: str = Field(min_length=1)


def build_material_router(
    auth_repository: AuthRepository,
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    material_submission_service: MaterialSubmissionService,
    material_deletion_service: MaterialDeletionService,
    audit_log_repository: AuditLogRepository,
) -> APIRouter:
    router = APIRouter(tags=["materials"])
    optional_request_identity = build_optional_request_identity_dependency(auth_repository)
    authenticated_request_identity = build_authenticated_request_identity_dependency(
        auth_repository
    )

    @router.post("/api/tasks/{task_id}/materials", status_code=status.HTTP_201_CREATED)
    async def submit_materials(
        task_id: str,
        request: Request,
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
                actor_id=resolved_submitter_id,
                channel=channel,
                material_type=material_type,
                files=uploaded_files,
                request_id=ensure_request_id(request),
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
        request: Request,
        channel: Annotated[SubmissionChannel, Form()],
        material_type: Annotated[MaterialType, Form()],
        files: Annotated[list[UploadFile], File(min_length=1)],
        task_id_hint: Annotated[str | None, Form()] = None,
        submitter_id_hint: Annotated[str | None, Form()] = None,
    ):
        uploaded_files = await read_uploaded_files(files)
        result = material_submission_service.submit_pending_assignment(
            actor_id=_build_pending_assignment_actor_id(
                channel=channel,
                submitter_id_hint=submitter_id_hint,
            ),
            channel=channel,
            material_type=material_type,
            files=uploaded_files,
            task_id_hint=task_id_hint,
            submitter_id_hint=submitter_id_hint,
            request_id=ensure_request_id(request),
        )
        return build_batch_response(result, file_count=len(uploaded_files))

    @router.post("/api/materials/{material_id}/claim")
    def claim_pending_assignment_material(
        material_id: str,
        request: Request,
        administrator_id: Annotated[str, Form(min_length=1)],
        task_id: Annotated[str, Form(min_length=1)],
        submitter_id: Annotated[str, Form(min_length=1)],
    ):
        request_id = ensure_request_id(request)
        material = material_repository.get(material_id)
        if material is None:
            _record_material_claim_audit(
                audit_log_repository,
                actor_id=administrator_id,
                material_id=material_id,
                task_id=task_id,
                submitter_id=submitter_id,
                result=AuditLogResult.FAILED,
                summary=f"fail to claim pending-assignment material {material_id}",
                detail={"failure_reason": "material not found"},
                request_id=request_id,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")
        if material.status is not MaterialStatus.PENDING_ASSIGNMENT:
            _record_material_claim_audit(
                audit_log_repository,
                actor_id=administrator_id,
                material_id=material_id,
                task_id=task_id,
                submitter_id=submitter_id,
                result=AuditLogResult.REJECTED,
                summary=f"reject claim for non-pending material {material_id}",
                detail={
                    "failure_reason": "material is not pending assignment",
                    "current_status": material.status,
                },
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="material is not pending assignment",
            )

        task = task_repository.get(task_id)
        if task is None:
            _record_material_claim_audit(
                audit_log_repository,
                actor_id=administrator_id,
                material_id=material_id,
                task_id=task_id,
                submitter_id=submitter_id,
                result=AuditLogResult.FAILED,
                summary=f"fail to claim material {material_id} into task {task_id}",
                detail={"failure_reason": "task not found"},
                request_id=request_id,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        if task.administrator_id != administrator_id:
            _record_material_claim_audit(
                audit_log_repository,
                actor_id=administrator_id,
                material_id=material_id,
                task_id=task_id,
                submitter_id=submitter_id,
                result=AuditLogResult.REJECTED,
                summary=f"reject unauthorized claim for material {material_id}",
                detail={
                    "failure_reason": "administrator is not allowed to claim materials for this task",
                    "task_administrator_id": task.administrator_id,
                },
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="administrator is not allowed to claim materials for this task",
            )

        try:
            ensure_task_has_member(task, submitter_id=submitter_id)
        except TaskSubmitterNotMemberError as error:
            _record_material_claim_audit(
                audit_log_repository,
                actor_id=administrator_id,
                material_id=material_id,
                task_id=task_id,
                submitter_id=submitter_id,
                result=AuditLogResult.REJECTED,
                summary=f"reject claim for material {material_id} with invalid submitter",
                detail={"failure_reason": str(error)},
                request_id=request_id,
            )
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
            _record_material_claim_audit(
                audit_log_repository,
                actor_id=administrator_id,
                material_id=material_id,
                task_id=task_id,
                submitter_id=submitter_id,
                result=AuditLogResult.REJECTED,
                summary=f"reject stale claim for material {material_id}",
                detail={"failure_reason": "material is not pending assignment"},
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="material is not pending assignment",
            )
        _record_material_claim_audit(
            audit_log_repository,
            actor_id=administrator_id,
            material_id=material_id,
            task_id=task_id,
            submitter_id=submitter_id,
            result=AuditLogResult.SUCCEEDED,
            summary=f"claim pending-assignment material {material_id}",
            detail={
                "claimed_status": claimed_material.status,
                "task_id_hint": claimed_material.task_id_hint,
                "submitter_id_hint": claimed_material.submitter_id_hint,
                "channel": claimed_material.channel,
                "material_type": claimed_material.material_type,
            },
            request_id=request_id,
        )
        return {"item": claimed_material}

    @router.post("/api/materials/{material_id}/deletion-mark")
    def mark_material_deleted(
        material_id: str,
        payload: MaterialDeletionMarkRequest,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        administrator_id = resolve_required_actor_request_field(
            identity,
            payload.administrator_id,
            field_name="administrator_id",
        )
        try:
            deleted_material = material_deletion_service.mark_deleted(
                material_id=material_id,
                actor_id=administrator_id,
            )
        except MaterialDeletionNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")
        except MaterialDeletionTaskNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        except MaterialDeletionActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except MaterialDeletionConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        return {"item": deleted_material}

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


def _build_pending_assignment_actor_id(
    *,
    channel: SubmissionChannel,
    submitter_id_hint: str | None,
) -> str:
    normalized_hint = (submitter_id_hint or "").strip()
    if normalized_hint:
        return normalized_hint[:128]
    return f"pending-assignment:{channel.value}"


def _record_material_claim_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    material_id: str,
    task_id: str,
    submitter_id: str,
    result: AuditLogResult,
    summary: str,
    detail: dict[str, object],
    request_id: str | None,
) -> None:
    audit_log_repository.create(
        AuditLogCreate(
            actor_id=actor_id,
            object_type="material",
            object_id=material_id,
            action="claim_pending_assignment",
            result=result,
            summary=summary,
            detail={
                "task_id": task_id,
                "submitter_id": submitter_id,
                **detail,
            },
            task_id=task_id,
            request_id=request_id,
        )
    )
