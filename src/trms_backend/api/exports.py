from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import PlainTextResponse

from trms_backend.domain.confirmations import ConfirmationRepository
from trms_backend.domain.exports import (
    ExportArtifactFormat,
    TaskExportActorNotAllowedError,
    TaskExportFormatNotSupportedError,
    TaskExportFormatNotImplementedError,
    TaskExportJobNotReadyError,
    TaskExportJobRepository,
    TaskExportJobRequest,
    TaskExportJobStatusTransitionError,
    TaskExportJobStatusUpdate,
    build_task_export_boundary,
    build_invoice_details_export,
    build_member_details_export,
    build_reimbursement_summary_export,
    create_task_export_job,
    list_task_export_jobs,
    render_invoice_details_csv,
    render_member_details_csv,
    render_reimbursement_summary_csv,
    update_task_export_job_status,
)
from trms_backend.domain.invoices import InvoiceRepository
from trms_backend.domain.materials import MaterialRepository
from trms_backend.domain.splits import ExpenseSplitRepository
from trms_backend.domain.tasks import TaskRepository
from trms_backend.domain.invoices import ValidationRepository


def build_export_router(
    task_repository: TaskRepository,
    export_job_repository: TaskExportJobRepository,
    invoice_repository: InvoiceRepository,
    material_repository: MaterialRepository,
    validation_repository: ValidationRepository,
    split_repository: ExpenseSplitRepository,
    confirmation_repository: ConfirmationRepository,
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

    @router.get("/{task_id}/exports/reimbursement-summary")
    def export_reimbursement_summary(
        task_id: str,
        actor_id: Annotated[str, Query(min_length=1)],
        format: ExportArtifactFormat = ExportArtifactFormat.CSV,
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoices = invoice_repository.list_by_task(task_id)
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }

        try:
            export = build_reimbursement_summary_export(
                task,
                actor_id=actor_id,
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
        actor_id: Annotated[str, Query(min_length=1)],
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

        try:
            export = build_member_details_export(
                task,
                actor_id=actor_id,
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
        actor_id: Annotated[str, Query(min_length=1)],
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

        try:
            export = build_invoice_details_export(
                task,
                actor_id=actor_id,
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
