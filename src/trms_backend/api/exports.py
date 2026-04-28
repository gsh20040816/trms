from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field, ValidationError

from trms_backend.api.error_responses import ensure_request_id
from trms_backend.api.request_identity import (
    RequestIdentity,
    build_authenticated_request_identity_dependency,
    build_optional_request_identity_dependency,
)
from trms_backend.api.request_identity_http import resolve_required_actor_request_field
from trms_backend.application.metrics import MetricsCollector, NoOpMetricsCollector
from trms_backend.application.export_audit import (
    record_export_job_created_audit,
    record_export_job_download_audit,
    record_export_job_terminal_status_audit,
)
from trms_backend.domain.audit_logs import AuditLogRepository
from trms_backend.domain.auth import AuthRepository
from trms_backend.domain.confirmations import ConfirmationRepository
from trms_backend.domain.exports import (
    ExportArtifactKind,
    ExportArtifactFormat,
    MergedPdfSourceMaterialError,
    TaskExportActorNotAllowedError,
    TaskExportFormatNotSupportedError,
    TaskExportFormatNotImplementedError,
    TaskExportJobNotReadyError,
    TaskExportJobRepository,
    TaskExportJobRequest,
    TaskExportJobStatus,
    TaskExportJobStatusTransitionError,
    TaskExportJobStatusUpdate,
    build_task_export_retry_counts,
    build_task_export_version_snapshot,
    build_finance_draft_export,
    build_invoice_details_export,
    build_member_details_export,
    build_merged_pdf_export_plan,
    build_missing_materials_export,
    build_reimbursement_summary_export,
    build_task_export_boundary,
    create_task_export_job,
    list_task_export_jobs,
    render_invoice_details_csv,
    render_member_details_csv,
    render_missing_materials_csv,
    render_reimbursement_summary_csv,
    update_task_export_job_status,
    with_task_export_job_latest_flag,
    with_task_export_job_retry_count,
)
from trms_backend.domain.invoices import InvoiceRepository
from trms_backend.domain.invoices import ValidationRepository
from trms_backend.domain.materials import MaterialFileStorage, MaterialRepository
from trms_backend.domain.splits import ExpenseSplitRepository
from trms_backend.domain.tasks import TaskRepository


class TaskExportJobRequestInput(BaseModel):
    actor_id: str | None = None
    kind: ExportArtifactKind
    format: ExportArtifactFormat
    parameters: dict[str, object] = Field(default_factory=dict)

    def to_domain(self, *, actor_id: str) -> TaskExportJobRequest:
        return TaskExportJobRequest.model_validate(
            {
                "actor_id": actor_id,
                "kind": self.kind,
                "format": self.format,
                "parameters": self.parameters,
            }
        )


class TaskExportJobStatusUpdateInput(BaseModel):
    actor_id: str | None = None
    target_status: TaskExportJobStatus
    failure_reason: str | None = None

    def to_domain(self, *, actor_id: str) -> TaskExportJobStatusUpdate:
        return TaskExportJobStatusUpdate.model_validate(
            {
                "actor_id": actor_id,
                "target_status": self.target_status,
                "failure_reason": self.failure_reason,
            }
        )


def build_export_router(
    auth_repository: AuthRepository,
    task_repository: TaskRepository,
    export_job_repository: TaskExportJobRepository,
    invoice_repository: InvoiceRepository,
    material_repository: MaterialRepository,
    material_file_storage: MaterialFileStorage,
    validation_repository: ValidationRepository,
    split_repository: ExpenseSplitRepository,
    confirmation_repository: ConfirmationRepository,
    audit_log_repository: AuditLogRepository,
    metrics_collector: MetricsCollector | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/tasks", tags=["exports"])
    optional_request_identity = build_optional_request_identity_dependency(auth_repository)
    authenticated_request_identity = build_authenticated_request_identity_dependency(
        auth_repository
    )
    metrics = metrics_collector or NoOpMetricsCollector()

    def build_current_export_snapshot(task):
        invoices = invoice_repository.list_by_task(task.id)
        materials = material_repository.list_by_task(task.id)
        validations_by_invoice_id = {
            invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation
        return build_task_export_version_snapshot(
            task,
            invoices=invoices,
            materials=materials,
            validations_by_invoice_id=validations_by_invoice_id,
            splits_by_invoice_id=splits_by_invoice_id,
            confirmations_by_split_id=confirmations_by_split_id,
        )

    def with_export_job_status_view(task, export_job):
        snapshot = build_current_export_snapshot(task)
        retry_counts = build_task_export_retry_counts(
            export_job_repository.list_by_task(task.id)
        )
        return with_task_export_job_retry_count(
            with_task_export_job_latest_flag(export_job, snapshot=snapshot),
            retry_count=retry_counts.get(export_job.id, 0),
        )

    @router.get("/{task_id}/exports/capabilities")
    def get_task_export_capabilities(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            return build_task_export_boundary(task, actor_id=resolved_actor_id)
        except TaskExportActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/exports/reimbursement-summary")
    def export_reimbursement_summary(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
        format: ExportArtifactFormat = ExportArtifactFormat.CSV,
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoices = invoice_repository.list_by_task(task_id)
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            export = build_reimbursement_summary_export(
                task,
                actor_id=resolved_actor_id,
                format=format,
                invoices=invoices,
                splits_by_invoice_id=splits_by_invoice_id,
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
        except TaskExportFormatNotImplementedError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

        return PlainTextResponse(
            content=render_reimbursement_summary_csv(export),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{export.filename}"',
            },
        )

    @router.get("/{task_id}/exports/member-details")
    def export_member_details(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
        format: ExportArtifactFormat = ExportArtifactFormat.CSV,
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoices = invoice_repository.list_by_task(task_id)
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            export = build_member_details_export(
                task,
                actor_id=resolved_actor_id,
                format=format,
                invoices=invoices,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
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
        except TaskExportFormatNotImplementedError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

        return PlainTextResponse(
            content=render_member_details_csv(export),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{export.filename}"',
            },
        )

    @router.get("/{task_id}/exports/invoice-details")
    def export_invoice_details(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
        format: ExportArtifactFormat = ExportArtifactFormat.CSV,
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoices = invoice_repository.list_by_task(task_id)
        materials_by_id = {
            material.id: material for material in material_repository.list_by_task(task_id)
        }
        validations_by_invoice_id = {
            invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            export = build_invoice_details_export(
                task,
                actor_id=resolved_actor_id,
                format=format,
                invoices=invoices,
                materials_by_id=materials_by_id,
                validations_by_invoice_id=validations_by_invoice_id,
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
        except TaskExportFormatNotImplementedError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

        return PlainTextResponse(
            content=render_invoice_details_csv(export),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{export.filename}"',
            },
        )

    @router.get("/{task_id}/exports/missing-materials")
    def export_missing_materials(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
        format: ExportArtifactFormat = ExportArtifactFormat.CSV,
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoices = invoice_repository.list_by_task(task_id)
        materials_by_id = {
            material.id: material for material in material_repository.list_by_task(task_id)
        }
        validations_by_invoice_id = {
            invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            export = build_missing_materials_export(
                task,
                actor_id=resolved_actor_id,
                format=format,
                invoices=invoices,
                materials_by_id=materials_by_id,
                validations_by_invoice_id=validations_by_invoice_id,
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
        except TaskExportFormatNotImplementedError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

        return PlainTextResponse(
            content=render_missing_materials_csv(export),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{export.filename}"',
            },
        )

    @router.get("/{task_id}/exports/finance-draft")
    def export_finance_draft(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
        format: ExportArtifactFormat = ExportArtifactFormat.JSON,
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoices = invoice_repository.list_by_task(task_id)
        materials_by_id = {
            material.id: material for material in material_repository.list_by_task(task_id)
        }
        validations_by_invoice_id = {
            invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            export = build_finance_draft_export(
                task,
                actor_id=resolved_actor_id,
                format=format,
                invoices=invoices,
                materials_by_id=materials_by_id,
                validations_by_invoice_id=validations_by_invoice_id,
                splits_by_invoice_id=splits_by_invoice_id,
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
        except TaskExportFormatNotImplementedError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

        return JSONResponse(
            content=export.model_dump(mode="json"),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{export.filename}"',
            },
        )

    @router.get("/{task_id}/exports/merged-pdf")
    def export_merged_pdf_plan(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
        format: ExportArtifactFormat = ExportArtifactFormat.PDF,
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        materials = material_repository.list_by_task(task_id)
        material_bytes_by_id: dict[str, bytes] = {}
        for material in materials:
            try:
                material_bytes_by_id[material.id] = material_file_storage.read(
                    storage_key=material.storage_key
                )
            except FileNotFoundError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"merged pdf source material {material.id} file content is missing from storage",
                ) from error

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            export_plan = build_merged_pdf_export_plan(
                task,
                actor_id=resolved_actor_id,
                format=format,
                materials=materials,
                material_bytes_by_id=material_bytes_by_id,
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
        except MergedPdfSourceMaterialError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

        return JSONResponse(
            content=export_plan.model_dump(mode="json"),
            media_type="application/json",
        )

    @router.post("/{task_id}/exports", status_code=status.HTTP_201_CREATED)
    def create_export_job(
        task_id: str,
        payload: TaskExportJobRequestInput,
        request: Request,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        snapshot = build_current_export_snapshot(task)

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            payload.actor_id,
            field_name="actor_id",
        )
        try:
            export_job = create_task_export_job(
                task,
                payload=payload.to_domain(actor_id=resolved_actor_id),
                snapshot=snapshot,
                repository=export_job_repository,
            )
            record_export_job_created_audit(
                audit_log_repository,
                actor_id=resolved_actor_id,
                export_job=export_job,
                request_id=ensure_request_id(request),
            )
            metrics.record_export_job_status(
                kind=export_job.kind,
                format=export_job.format,
                status=export_job.status,
            )
            return with_export_job_status_view(task, export_job)
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
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
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            export_jobs = list_task_export_jobs(
                task,
                actor_id=resolved_actor_id,
                repository=export_job_repository,
            )
            return [with_export_job_status_view(task, export_job) for export_job in export_jobs]
        except TaskExportActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/exports/{export_job_id}")
    def get_export_job(
        export_job_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        export_job = export_job_repository.get(export_job_id)
        if export_job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="export job not found",
            )

        task = task_repository.get(export_job.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            list_task_export_jobs(
                task,
                actor_id=resolved_actor_id,
                repository=export_job_repository,
            )
        except TaskExportActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

        return with_export_job_status_view(task, export_job)

    @router.get("/exports/{export_job_id}/artifact")
    def download_export_job_artifact(
        export_job_id: str,
        request: Request,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        export_job = export_job_repository.get(export_job_id)
        if export_job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="export job not found",
            )

        task = task_repository.get(export_job.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            list_task_export_jobs(
                task,
                actor_id=resolved_actor_id,
                repository=export_job_repository,
            )
        except TaskExportActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

        if export_job.artifact is None or export_job.artifact_storage_key is None:
            if export_job.status is TaskExportJobStatus.FAILED:
                failure_reason = export_job.failure_reason or "unknown failure"
                detail = (
                    "export artifact is unavailable because the job failed: "
                    f"{failure_reason}"
                )
            else:
                detail = f"export artifact is not ready; current status is {export_job.status.value}"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            )

        try:
            content = material_file_storage.read(storage_key=export_job.artifact_storage_key)
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="export artifact file is missing from storage",
            ) from error

        record_export_job_download_audit(
            audit_log_repository,
            actor_id=resolved_actor_id,
            export_job=export_job,
            request_id=ensure_request_id(request),
        )
        return Response(
            content=content,
            media_type=export_job.artifact.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{export_job.artifact.filename}"',
            },
        )

    @router.patch("/exports/{export_job_id}/status")
    def update_export_job_status(
        export_job_id: str,
        payload: TaskExportJobStatusUpdateInput,
        request: Request,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        export_job = export_job_repository.get(export_job_id)
        if export_job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="export job not found",
            )

        task = task_repository.get(export_job.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            payload.actor_id,
            field_name="actor_id",
        )
        try:
            previous_status = export_job.status
            updated = update_task_export_job_status(
                task,
                export_job=export_job,
                payload=payload.to_domain(actor_id=resolved_actor_id),
                repository=export_job_repository,
            )
            record_export_job_terminal_status_audit(
                audit_log_repository,
                actor_id=resolved_actor_id,
                export_job=updated,
                previous_status=previous_status,
                request_id=ensure_request_id(request),
            )
            metrics.record_export_job_status(
                kind=updated.kind,
                format=updated.format,
                status=updated.status,
            )
            return with_export_job_status_view(task, updated)
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
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
