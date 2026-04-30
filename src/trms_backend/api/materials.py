from collections.abc import Callable
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, Field

from trms_backend.api.error_responses import ensure_request_id
from trms_backend.api.invoice_validation_refresh import (
    refresh_invoice_validations,
    refresh_validations_for_material,
)
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
from trms_backend.application.material_type_update import (
    MaterialTypeUpdateActorNotAllowedError,
    MaterialTypeUpdateConflictError,
    MaterialTypeUpdateNotFoundError,
    MaterialTypeUpdateService,
    MaterialTypeUpdateTaskNotFoundError,
)
from trms_backend.application.metrics import MetricsCollector, NoOpMetricsCollector
from trms_backend.application.material_submission import (
    MaterialSubmissionService,
    MaterialSubmissionTaskNotFoundError,
    MaterialSubmissionTaskNotOpenError,
)
from trms_backend.application.recognition_preparation import (
    RecognitionMaterialNotFoundError,
    RecognitionPreparationService,
    RecognitionTaskExecutionConflictError,
    RecognitionTaskExecutionNotFoundError,
)
from trms_backend.application.recognition_invoice_auto_create import (
    RecognitionInvoiceAutoCreateService,
)
from trms_backend.application.recognition_audit import record_recognition_result_audit
from trms_backend.application.supporting_material_auto_link import (
    SupportingMaterialAutoLinkService,
)
from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
from trms_backend.domain.auth import AuthRepository
from trms_backend.domain.invoices import InvoiceRepository, ValidationRepository
from trms_backend.domain.materials import (
    MaterialStatus,
    MaterialRepository,
    MaterialType,
    SubmissionChannel,
)
from trms_backend.domain.recognitions import RecognitionTaskRepository
from trms_backend.domain.recognitions import (
    RecognitionFailureDetail,
    RecognitionFailureStage,
    RecognitionResultPayload,
    RecognitionTaskStatus,
)
from trms_backend.runtime_config import AsyncJobMode
from trms_backend.domain.tasks import (
    TaskRepository,
    TaskSubmissionDeadlinePassedError,
    TaskSubmitterNotMemberError,
    ensure_task_has_member,
)


class MaterialDeletionMarkRequest(BaseModel):
    administrator_id: str = Field(min_length=1)


class MaterialTypeUpdateRequest(BaseModel):
    actor_id: str | None = None
    material_type: MaterialType


def _resolve_uploaded_material_type(material_type: MaterialType | None) -> MaterialType:
    return material_type or MaterialType.OTHER_ATTACHMENT


def build_material_router(
    auth_repository: AuthRepository,
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    validation_repository: ValidationRepository,
    recognition_task_repository: RecognitionTaskRepository,
    material_submission_service: MaterialSubmissionService,
    recognition_preparation_service: RecognitionPreparationService,
    material_deletion_service: MaterialDeletionService,
    material_type_update_service: MaterialTypeUpdateService,
    audit_log_repository: AuditLogRepository,
    async_job_mode: AsyncJobMode,
    metrics_collector: MetricsCollector | None = None,
    recognition_provider_configured_resolver: Callable[[], bool] | None = None,
) -> APIRouter:
    router = APIRouter(tags=["materials"])
    optional_request_identity = build_optional_request_identity_dependency(auth_repository)
    authenticated_request_identity = build_authenticated_request_identity_dependency(
        auth_repository
    )
    metrics = metrics_collector or NoOpMetricsCollector()
    supporting_material_auto_link_service = SupportingMaterialAutoLinkService(
        material_repository=material_repository,
        invoice_repository=invoice_repository,
    )
    recognition_invoice_auto_create_service = RecognitionInvoiceAutoCreateService(
        task_repository=task_repository,
        material_repository=material_repository,
        invoice_repository=invoice_repository,
        supporting_material_auto_link_service=supporting_material_auto_link_service,
    )

    def dispatch_recognition_tasks_for_uploaded_materials(
        *,
        material_ids: list[str],
        actor_id: str,
        request_id: str,
    ) -> tuple[dict[str, str], dict[str, str]]:
        recognition_status_by_material_id = {
            material_id: "pending"
            for material_id in material_ids
        }
        if async_job_mode == "worker":
            return recognition_status_by_material_id, {
                "mode": "worker",
                "status": "queued",
                "message": "识别已入队等待 worker 消费；在 worker 未运行前，材料会保持“识别排队中”。",
            }

        if (
            recognition_provider_configured_resolver is not None
            and not recognition_provider_configured_resolver()
        ):
            failure = RecognitionFailureDetail(
                stage=RecognitionFailureStage.AI,
                reason="llm_provider_not_configured",
            )
            for material_id in material_ids:
                recognition_tasks = recognition_task_repository.list_by_material(material_id)
                material = material_repository.get(material_id)
                if not recognition_tasks or material is None:
                    continue
                latest_task = recognition_tasks[-1]
                updated = recognition_task_repository.update_status(
                    latest_task.id,
                    RecognitionTaskStatus.FAILED,
                    result=RecognitionResultPayload(
                        raw_response={
                            "preparation": {
                                "material_id": material.id,
                                "original_filename": material.original_filename,
                                "content_type": material.content_type,
                            }
                        }
                    ),
                    failure=failure,
                    expected_current_status=RecognitionTaskStatus.PENDING,
                )
                if updated is None:
                    continue
                record_recognition_result_audit(
                    audit_log_repository,
                    actor_id=actor_id,
                    recognition_task=updated,
                    task_id=material.task_id,
                    request_id=request_id,
                )
                metrics.record_recognition_task_status(
                    status=updated.status,
                    failure_stage=failure.stage,
                )
                recognition_status_by_material_id[material_id] = updated.status.value
            return recognition_status_by_material_id, {
                "mode": "in_process",
                "status": "executed",
                "message": "当前环境未配置识别服务；材料已接收，但无法自动识别，请配置 provider 或手动补录。",
            }

        for material_id in material_ids:
            recognition_tasks = recognition_task_repository.list_by_material(material_id)
            if not recognition_tasks:
                continue
            latest_task = recognition_tasks[-1]
            try:
                updated = recognition_preparation_service.execute(
                    latest_task.id,
                    actor_id=actor_id,
                    request_id=request_id,
                )
            except (
                RecognitionTaskExecutionNotFoundError,
                RecognitionTaskExecutionConflictError,
                RecognitionMaterialNotFoundError,
            ):
                continue
            recognition_invoice_auto_create_service.try_upsert_invoice_from_recognition(updated)
            refresh_validations_for_material(
                updated.material_id,
                task_repository=task_repository,
                material_repository=material_repository,
                invoice_repository=invoice_repository,
                validation_repository=validation_repository,
                recognition_task_repository=recognition_task_repository,
                metrics_collector=metrics,
            )
            recognition_status_by_material_id[material_id] = updated.status.value

        return recognition_status_by_material_id, {
            "mode": "in_process",
            "status": "executed",
            "message": "识别已在当前请求内执行；如结果仍待确认，请继续补录或复核关键字段。",
        }

    @router.post("/api/tasks/{task_id}/materials", status_code=status.HTTP_201_CREATED)
    async def submit_materials(
        task_id: str,
        request: Request,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
        channel: Annotated[SubmissionChannel, Form()],
        files: Annotated[list[UploadFile], File(min_length=1)],
        material_type: Annotated[MaterialType | None, Form()] = None,
        submitter_id: Annotated[str | None, Form(min_length=1)] = None,
    ):
        uploaded_files = await read_uploaded_files(files)
        resolved_submitter_id = resolve_required_actor_request_field(
            identity,
            submitter_id,
            field_name="submitter_id",
        )
        resolved_material_type = _resolve_uploaded_material_type(material_type)
        try:
            result = material_submission_service.submit_to_task(
                task_id=task_id,
                submitter_id=resolved_submitter_id,
                actor_id=resolved_submitter_id,
                channel=channel,
                material_type=resolved_material_type,
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

        auto_linked_invoice_ids: set[str] = set()
        for record in result.records:
            for link in supporting_material_auto_link_service.auto_link_for_material(record):
                auto_linked_invoice_ids.add(link.invoice_id)
        for invoice_id in auto_linked_invoice_ids:
            refresh_invoice_validations(
                invoice_id,
                task_repository=task_repository,
                material_repository=material_repository,
                invoice_repository=invoice_repository,
                validation_repository=validation_repository,
                recognition_task_repository=recognition_task_repository,
                metrics_collector=metrics,
            )

        recognition_status_by_material_id, recognition_dispatch = dispatch_recognition_tasks_for_uploaded_materials(
            material_ids=[record.id for record in result.records],
            actor_id=resolved_submitter_id,
            request_id=ensure_request_id(request),
        )
        encoded_items = [
            {
                **(material_repository.get(item.id) or item).model_dump(mode="json"),
                "recognition_status": recognition_status_by_material_id.get(item.id, "pending"),
            }
            for item in result.records
        ]
        return build_batch_response(
            result,
            file_count=len(uploaded_files),
            extra_body={
                "items": encoded_items,
                "recognition_dispatch": recognition_dispatch,
            },
        )

    @router.post("/api/materials/pending-assignment", status_code=status.HTTP_201_CREATED)
    async def submit_pending_assignment_materials(
        request: Request,
        channel: Annotated[SubmissionChannel, Form()],
        files: Annotated[list[UploadFile], File(min_length=1)],
        material_type: Annotated[MaterialType | None, Form()] = None,
        task_id_hint: Annotated[str | None, Form()] = None,
        submitter_id_hint: Annotated[str | None, Form()] = None,
    ):
        uploaded_files = await read_uploaded_files(files)
        resolved_material_type = _resolve_uploaded_material_type(material_type)
        result = material_submission_service.submit_pending_assignment(
            actor_id=_build_pending_assignment_actor_id(
                channel=channel,
                submitter_id_hint=submitter_id_hint,
            ),
            channel=channel,
            material_type=resolved_material_type,
            files=uploaded_files,
            task_id_hint=task_id_hint,
            submitter_id_hint=submitter_id_hint,
            request_id=ensure_request_id(request),
        )
        recognition_status_by_material_id, recognition_dispatch = dispatch_recognition_tasks_for_uploaded_materials(
            material_ids=[record.id for record in result.records],
            actor_id=_build_pending_assignment_actor_id(
                channel=channel,
                submitter_id_hint=submitter_id_hint,
            ),
            request_id=ensure_request_id(request),
        )
        encoded_items = [
            {
                **(material_repository.get(item.id) or item).model_dump(mode="json"),
                "recognition_status": recognition_status_by_material_id.get(item.id, "pending"),
            }
            for item in result.records
        ]
        return build_batch_response(
            result,
            file_count=len(uploaded_files),
            extra_body={
                "items": encoded_items,
                "recognition_dispatch": recognition_dispatch,
            },
        )

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
        request: Request,
        payload: MaterialDeletionMarkRequest,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        request_id = ensure_request_id(request)
        try:
            administrator_id = resolve_required_actor_request_field(
                identity,
                payload.administrator_id,
                field_name="administrator_id",
            )
        except HTTPException as error:
            _record_material_deletion_audit(
                audit_log_repository,
                actor_id=identity.actor_id or payload.administrator_id,
                material_id=material_id,
                task_id=None,
                result=AuditLogResult.REJECTED,
                summary=f"reject deletion mark for material {material_id}",
                detail={
                    "failure_reason": error.detail,
                    "requested_administrator_id": payload.administrator_id,
                },
                request_id=request_id,
            )
            raise

        material = material_repository.get(material_id)
        try:
            deleted_material = material_deletion_service.mark_deleted(
                material_id=material_id,
                actor_id=administrator_id,
            )
        except MaterialDeletionNotFoundError:
            _record_material_deletion_audit(
                audit_log_repository,
                actor_id=administrator_id,
                material_id=material_id,
                task_id=None,
                result=AuditLogResult.FAILED,
                summary=f"fail to mark material {material_id} deleted",
                detail={"failure_reason": "material not found"},
                request_id=request_id,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")
        except MaterialDeletionTaskNotFoundError as error:
            _record_material_deletion_audit(
                audit_log_repository,
                actor_id=administrator_id,
                material_id=material_id,
                task_id=error.task_id,
                result=AuditLogResult.FAILED,
                summary=f"fail to mark material {material_id} deleted",
                detail={"failure_reason": "task not found"},
                request_id=request_id,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        except MaterialDeletionActorNotAllowedError as error:
            _record_material_deletion_audit(
                audit_log_repository,
                actor_id=administrator_id,
                material_id=material_id,
                task_id=material.task_id if material is not None else None,
                result=AuditLogResult.REJECTED,
                summary=f"reject unauthorized deletion mark for material {material_id}",
                detail={"failure_reason": str(error)},
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except MaterialDeletionConflictError as error:
            _record_material_deletion_audit(
                audit_log_repository,
                actor_id=administrator_id,
                material_id=material_id,
                task_id=material.task_id if material is not None else None,
                result=AuditLogResult.REJECTED,
                summary=f"reject deletion mark for material {material_id}",
                detail={
                    "failure_reason": str(error),
                    "current_status": material.status if material is not None else None,
                },
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        _record_material_deletion_audit(
            audit_log_repository,
            actor_id=administrator_id,
            material_id=material_id,
            task_id=deleted_material.task_id,
            result=AuditLogResult.SUCCEEDED,
            summary=f"mark material {material_id} deleted",
            detail={
                "deleted_status": deleted_material.status,
                "submitter_id": deleted_material.submitter_id,
                "channel": deleted_material.channel,
                "material_type": deleted_material.material_type,
                "original_filename": deleted_material.original_filename,
            },
            request_id=request_id,
        )
        return {"item": deleted_material}

    @router.patch("/api/materials/{material_id}/material-type")
    def update_material_type(
        material_id: str,
        request: Request,
        payload: MaterialTypeUpdateRequest,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        request_id = ensure_request_id(request)
        try:
            actor_id = resolve_required_actor_request_field(
                identity,
                payload.actor_id,
                field_name="actor_id",
            )
        except HTTPException as error:
            _record_material_type_update_audit(
                audit_log_repository,
                actor_id=identity.actor_id or payload.actor_id or "",
                material_id=material_id,
                task_id=None,
                result=AuditLogResult.REJECTED,
                summary=f"reject material type update for {material_id}",
                detail={
                    "failure_reason": error.detail,
                    "requested_actor_id": payload.actor_id,
                    "requested_material_type": payload.material_type.value,
                },
                request_id=request_id,
            )
            raise

        existing_material = material_repository.get(material_id)
        try:
            updated_material = material_type_update_service.update_material_type(
                material_id=material_id,
                actor_id=actor_id,
                material_type=payload.material_type,
            )
        except MaterialTypeUpdateNotFoundError:
            _record_material_type_update_audit(
                audit_log_repository,
                actor_id=actor_id,
                material_id=material_id,
                task_id=None,
                result=AuditLogResult.FAILED,
                summary=f"fail to update material type for {material_id}",
                detail={
                    "failure_reason": "material not found",
                    "requested_material_type": payload.material_type.value,
                },
                request_id=request_id,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")
        except MaterialTypeUpdateTaskNotFoundError as error:
            _record_material_type_update_audit(
                audit_log_repository,
                actor_id=actor_id,
                material_id=material_id,
                task_id=error.task_id,
                result=AuditLogResult.FAILED,
                summary=f"fail to update material type for {material_id}",
                detail={
                    "failure_reason": "task not found",
                    "requested_material_type": payload.material_type.value,
                },
                request_id=request_id,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        except MaterialTypeUpdateActorNotAllowedError as error:
            _record_material_type_update_audit(
                audit_log_repository,
                actor_id=actor_id,
                material_id=material_id,
                task_id=existing_material.task_id if existing_material is not None else None,
                result=AuditLogResult.REJECTED,
                summary=f"reject material type update for {material_id}",
                detail={
                    "failure_reason": str(error),
                    "requested_material_type": payload.material_type.value,
                },
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except MaterialTypeUpdateConflictError as error:
            _record_material_type_update_audit(
                audit_log_repository,
                actor_id=actor_id,
                material_id=material_id,
                task_id=existing_material.task_id if existing_material is not None else None,
                result=AuditLogResult.REJECTED,
                summary=f"reject material type update for {material_id}",
                detail={
                    "failure_reason": str(error),
                    "current_material_type": (
                        existing_material.material_type.value if existing_material is not None else None
                    ),
                    "requested_material_type": payload.material_type.value,
                },
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        refresh_validations_for_material(
            material_id,
            task_repository=task_repository,
            material_repository=material_repository,
            invoice_repository=invoice_repository,
            validation_repository=validation_repository,
            recognition_task_repository=recognition_task_repository,
            metrics_collector=metrics,
        )
        _record_material_type_update_audit(
            audit_log_repository,
            actor_id=actor_id,
            material_id=material_id,
            task_id=updated_material.task_id,
            result=AuditLogResult.SUCCEEDED,
            summary=f"update material type for {material_id}",
            detail={
                "previous_material_type": (
                    existing_material.material_type.value if existing_material is not None else None
                ),
                "updated_material_type": updated_material.material_type.value,
                "submitter_id": updated_material.submitter_id,
            },
            request_id=request_id,
        )
        return {"item": updated_material}

    @router.get("/api/tasks/{task_id}/materials")
    def list_materials(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
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

    @router.get("/api/materials/{material_id}/content")
    def get_material_content(
        material_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")
        if material.status is not MaterialStatus.ASSIGNED or material.task_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="material is not available for preview",
            )

        task = task_repository.get(material.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to view this material content",
        )
        if scope is TaskAccessScope.MEMBER and material.submitter_id != identity.actor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="actor is not allowed to view this material content",
            )

        content = material_submission_service.read_material_content(storage_key=material.storage_key)
        media_type = material.content_type or "application/octet-stream"
        filename = material.original_filename.replace('"', "")
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": _build_inline_content_disposition(filename)},
        )

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


def _build_inline_content_disposition(filename: str) -> str:
    sanitized = filename.replace('"', "")
    try:
        sanitized.encode("latin-1")
    except UnicodeEncodeError:
        ascii_fallback = "".join(
            character if 32 <= ord(character) < 127 and character not in {'"', "\\", ";"}
            else "_"
            for character in sanitized
        ).strip("._") or "material"
        encoded_filename = quote(sanitized, safe="")
        return f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_filename}"
    return f'inline; filename="{sanitized}"'


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


def _record_material_deletion_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    material_id: str,
    task_id: str | None,
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
            action="mark_material_deleted",
            result=result,
            summary=summary,
            detail=detail,
            task_id=task_id,
            request_id=request_id,
        )
    )


def _record_material_type_update_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    material_id: str,
    task_id: str | None,
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
            action="update_material_type",
            result=result,
            summary=summary,
            detail=detail,
            task_id=task_id,
            request_id=request_id,
        )
    )
