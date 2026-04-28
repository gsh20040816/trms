from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from trms_backend.api.error_responses import ensure_request_id
from trms_backend.api.invoice_validation_refresh import refresh_validations_for_material
from trms_backend.api.request_identity import (
    RequestIdentity,
    build_authenticated_request_identity_dependency,
    build_optional_request_identity_dependency,
)
from trms_backend.api.request_task_access import TaskAccessScope, resolve_task_access_scope
from trms_backend.application.metrics import MetricsCollector, NoOpMetricsCollector
from trms_backend.application.recognition_audit import record_recognition_result_audit
from trms_backend.application.recognition_preparation import (
    RecognitionMaterialNotFoundError,
    RecognitionPreparationService,
    RecognitionTaskExecutionConflictError,
    RecognitionTaskExecutionNotFoundError,
)
from trms_backend.domain.audit_logs import AuditLogRepository
from trms_backend.domain.auth import UserRole
from trms_backend.domain.auth import AuthRepository
from trms_backend.domain.invoices import InvoiceRepository, ValidationRepository
from trms_backend.domain.materials import MaterialRepository
from trms_backend.domain.recognitions import (
    RecognitionTaskCreate,
    RecognitionTaskRepository,
    RecognitionTaskStatusTransitionError,
    RecognitionTaskStatusUpdate,
    ensure_recognition_task_can_transition,
)
from trms_backend.domain.tasks import TaskRepository


def build_recognition_router(
    auth_repository: AuthRepository,
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    validation_repository: ValidationRepository,
    recognition_task_repository: RecognitionTaskRepository,
    recognition_preparation_service: RecognitionPreparationService,
    audit_log_repository: AuditLogRepository,
    metrics_collector: MetricsCollector | None = None,
) -> APIRouter:
    router = APIRouter(tags=["recognitions"])
    optional_request_identity = build_optional_request_identity_dependency(auth_repository)
    authenticated_request_identity = build_authenticated_request_identity_dependency(
        auth_repository
    )
    metrics = metrics_collector or NoOpMetricsCollector()

    def ensure_recognition_task_manager_access(
        *,
        identity: RequestIdentity,
        material_id: str,
        forbidden_detail: str,
    ) -> None:
        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")

        if material.task_id is None:
            if identity.role not in {UserRole.ADMIN, UserRole.SYSTEM_ADMIN}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=forbidden_detail,
                )
            return

        task = task_repository.get(material.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail=forbidden_detail,
        )
        if scope is not TaskAccessScope.ADMINISTRATOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=forbidden_detail,
            )

    def ensure_recognition_task_retry_access(
        *,
        identity: RequestIdentity,
        material_id: str,
        forbidden_detail: str,
    ) -> None:
        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")

        if material.task_id is None:
            if identity.role not in {UserRole.ADMIN, UserRole.SYSTEM_ADMIN}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=forbidden_detail,
                )
            return

        task = task_repository.get(material.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail=forbidden_detail,
        )
        if scope is TaskAccessScope.ADMINISTRATOR:
            return
        if scope is TaskAccessScope.MEMBER and material.submitter_id == identity.actor_id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=forbidden_detail,
        )

    @router.post(
        "/api/materials/{material_id}/recognition-tasks",
        status_code=status.HTTP_201_CREATED,
    )
    def create_recognition_task(
        material_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        ensure_recognition_task_retry_access(
            identity=identity,
            material_id=material_id,
            forbidden_detail="actor is not allowed to retry recognition tasks for this material",
        )
        task = recognition_task_repository.create(RecognitionTaskCreate(material_id=material_id))
        metrics.record_recognition_task_status(status=task.status)
        return {"item": task}

    @router.get("/api/materials/{material_id}/recognition-tasks")
    def list_recognition_tasks(
        material_id: str,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")

        if material.task_id is not None:
            task = task_repository.get(material.task_id)
            if task is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
            scope = resolve_task_access_scope(
                identity,
                task,
                forbidden_detail="actor is not allowed to view recognition tasks for this material",
            )
            if scope is TaskAccessScope.MEMBER and material.submitter_id != identity.actor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="actor is not allowed to view recognition tasks for this material",
                )

        items = recognition_task_repository.list_by_material(material_id)

        return {
            "latest_effective": recognition_task_repository.get_latest_effective_by_material(material_id),
            "retry_count": max(len(items) - 1, 0),
            "items": items,
        }

    @router.patch("/api/recognition-tasks/{recognition_task_id}/status")
    def update_recognition_task_status(
        recognition_task_id: str,
        request: Request,
        payload: RecognitionTaskStatusUpdate,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = recognition_task_repository.get(recognition_task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="recognition task not found",
            )
        ensure_recognition_task_manager_access(
            identity=identity,
            material_id=task.material_id,
            forbidden_detail="actor is not allowed to manage recognition tasks for this material",
        )
        try:
            ensure_recognition_task_can_transition(task.status, payload.target_status)
        except RecognitionTaskStatusTransitionError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

        updated = recognition_task_repository.update_status(
            recognition_task_id,
            payload.target_status,
            payload.result,
            payload.failure,
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="recognition task not found",
            )
        refresh_validations_for_material(
            updated.material_id,
            task_repository=task_repository,
            material_repository=material_repository,
            invoice_repository=invoice_repository,
            validation_repository=validation_repository,
            recognition_task_repository=recognition_task_repository,
            metrics_collector=metrics,
        )
        metrics.record_recognition_task_status(
            status=updated.status,
            failure_stage=updated.failure.stage if updated.failure is not None else None,
        )
        if payload.result is not None or payload.failure is not None:
            material = material_repository.get(updated.material_id)
            record_recognition_result_audit(
                audit_log_repository,
                actor_id=identity.actor_id,
                recognition_task=updated,
                task_id=material.task_id if material is not None else None,
                request_id=ensure_request_id(request),
            )
        return {"item": updated}

    @router.post("/api/recognition-tasks/{recognition_task_id}/execute")
    def execute_recognition_task(
        recognition_task_id: str,
        request: Request,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = recognition_task_repository.get(recognition_task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="recognition task not found",
            )
        ensure_recognition_task_retry_access(
            identity=identity,
            material_id=task.material_id,
            forbidden_detail="actor is not allowed to retry recognition tasks for this material",
        )
        try:
            updated = recognition_preparation_service.execute(
                recognition_task_id,
                actor_id=identity.actor_id,
                request_id=ensure_request_id(request),
            )
        except RecognitionTaskExecutionNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        except RecognitionMaterialNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        except RecognitionTaskExecutionConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        refresh_validations_for_material(
            updated.material_id,
            task_repository=task_repository,
            material_repository=material_repository,
            invoice_repository=invoice_repository,
            validation_repository=validation_repository,
            recognition_task_repository=recognition_task_repository,
            metrics_collector=metrics,
        )
        return {"item": updated}

    return router
