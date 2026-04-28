from __future__ import annotations

import json

from trms_backend.application.async_jobs import AsyncJobProcessor
from trms_backend.application.export_audit import (
    SYSTEM_EXPORT_ACTOR_ID,
    record_export_job_terminal_status_audit,
)
from trms_backend.domain.audit_logs import AuditLogRepository
from trms_backend.domain.confirmations import ConfirmationRepository
from trms_backend.domain.exports import (
    ExportArtifactFormat,
    ExportArtifactKind,
    StoredExportArtifactRecord,
    TaskExportFormatNotImplementedError,
    TaskExportJobRecord,
    TaskExportJobRepository,
    TaskExportJobStatus,
    build_finance_draft_export,
    build_invoice_details_export,
    build_member_details_export,
    build_missing_materials_export,
    build_reimbursement_summary_export,
    build_task_export_version_snapshot,
    render_invoice_details_csv,
    render_member_details_csv,
    render_missing_materials_csv,
    render_reimbursement_summary_csv,
)
from trms_backend.domain.invoices import InvoiceRepository, ValidationRepository
from trms_backend.domain.materials import MaterialFileStorage, MaterialRepository
from trms_backend.domain.splits import ExpenseSplitRepository
from trms_backend.domain.tasks import ReimbursementTask, TaskRepository


class ExportAsyncJobProcessor(AsyncJobProcessor):
    job_type = "export"

    def __init__(
        self,
        *,
        task_repository: TaskRepository,
        export_job_repository: TaskExportJobRepository,
        invoice_repository: InvoiceRepository,
        material_repository: MaterialRepository,
        material_file_storage: MaterialFileStorage,
        validation_repository: ValidationRepository,
        split_repository: ExpenseSplitRepository,
        confirmation_repository: ConfirmationRepository,
        audit_log_repository: AuditLogRepository,
        batch_size: int = 10,
    ) -> None:
        self._task_repository = task_repository
        self._export_job_repository = export_job_repository
        self._invoice_repository = invoice_repository
        self._material_repository = material_repository
        self._material_file_storage = material_file_storage
        self._validation_repository = validation_repository
        self._split_repository = split_repository
        self._confirmation_repository = confirmation_repository
        self._audit_log_repository = audit_log_repository
        self._batch_size = batch_size

    def run_once(self) -> int:
        processed_count = 0
        for export_job in self._export_job_repository.list_pending(limit=self._batch_size):
            claimed = self._export_job_repository.update_status(
                export_job.id,
                target_status=TaskExportJobStatus.RUNNING,
                expected_current_status=TaskExportJobStatus.PENDING,
            )
            if claimed is None:
                continue

            task = self._task_repository.get(claimed.task_id)
            if task is None:
                self._fail_job(claimed.id, "task not found")
                processed_count += 1
                continue

            try:
                current_snapshot = self._build_current_export_snapshot(task)
                if (
                    claimed.task_data_version is not None
                    and current_snapshot.task_data_version != claimed.task_data_version
                ):
                    raise ValueError(
                        "task data changed since export job was requested; create a new export job"
                    )
                artifact = self._build_export_artifact(task, claimed)
            except Exception as error:
                self._fail_job(claimed.id, str(error))
                processed_count += 1
                continue

            updated = self._export_job_repository.update_status(
                claimed.id,
                target_status=TaskExportJobStatus.SUCCEEDED,
                artifact=artifact,
                expected_current_status=TaskExportJobStatus.RUNNING,
            )
            if updated is not None:
                record_export_job_terminal_status_audit(
                    self._audit_log_repository,
                    actor_id=SYSTEM_EXPORT_ACTOR_ID,
                    export_job=updated,
                    previous_status=TaskExportJobStatus.RUNNING,
                    request_id=None,
                )
            processed_count += 1
        return processed_count

    def _fail_job(self, export_job_id: str, reason: str) -> None:
        updated = self._export_job_repository.update_status(
            export_job_id,
            target_status=TaskExportJobStatus.FAILED,
            failure_reason=reason,
            expected_current_status=TaskExportJobStatus.RUNNING,
        )
        if updated is not None:
            record_export_job_terminal_status_audit(
                self._audit_log_repository,
                actor_id=SYSTEM_EXPORT_ACTOR_ID,
                export_job=updated,
                previous_status=TaskExportJobStatus.RUNNING,
                request_id=None,
            )

    def _build_current_export_snapshot(self, task: ReimbursementTask):
        invoices = self._invoice_repository.list_by_task(task.id)
        materials = self._material_repository.list_by_task(task.id)
        validations_by_invoice_id = {
            invoice.id: self._validation_repository.list_by_invoice(invoice.id)
            for invoice in invoices
        }
        splits_by_invoice_id = {
            invoice.id: self._split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in self._confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation
        return build_task_export_version_snapshot(
            task,
            invoices=invoices,
            materials=materials,
            validations_by_invoice_id=validations_by_invoice_id,
            splits_by_invoice_id=splits_by_invoice_id,
            confirmations_by_split_id=confirmations_by_split_id,
        )

    def _build_export_artifact(
        self,
        task: ReimbursementTask,
        export_job: TaskExportJobRecord,
    ) -> StoredExportArtifactRecord:
        invoices = self._invoice_repository.list_by_task(task.id)
        materials = self._material_repository.list_by_task(task.id)
        materials_by_id = {material.id: material for material in materials}
        validations_by_invoice_id = {
            invoice.id: self._validation_repository.list_by_invoice(invoice.id)
            for invoice in invoices
        }
        splits_by_invoice_id = {
            invoice.id: self._split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in self._confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation

        if export_job.kind is ExportArtifactKind.REIMBURSEMENT_SUMMARY:
            export = build_reimbursement_summary_export(
                task,
                actor_id=export_job.requested_by,
                format=export_job.format,
                invoices=invoices,
                splits_by_invoice_id=splits_by_invoice_id,
            )
            return self._save_artifact(
                task_id=task.id,
                filename=export.filename,
                content_type="text/csv",
                content=render_reimbursement_summary_csv(export).encode("utf-8"),
            )

        if export_job.kind is ExportArtifactKind.MEMBER_DETAILS:
            export = build_member_details_export(
                task,
                actor_id=export_job.requested_by,
                format=export_job.format,
                invoices=invoices,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
            )
            return self._save_artifact(
                task_id=task.id,
                filename=export.filename,
                content_type="text/csv",
                content=render_member_details_csv(export).encode("utf-8"),
            )

        if export_job.kind is ExportArtifactKind.INVOICE_DETAILS:
            export = build_invoice_details_export(
                task,
                actor_id=export_job.requested_by,
                format=export_job.format,
                invoices=invoices,
                materials_by_id=materials_by_id,
                validations_by_invoice_id=validations_by_invoice_id,
            )
            return self._save_artifact(
                task_id=task.id,
                filename=export.filename,
                content_type="text/csv",
                content=render_invoice_details_csv(export).encode("utf-8"),
            )

        if export_job.kind is ExportArtifactKind.MISSING_MATERIALS:
            export = build_missing_materials_export(
                task,
                actor_id=export_job.requested_by,
                format=export_job.format,
                invoices=invoices,
                materials_by_id=materials_by_id,
                validations_by_invoice_id=validations_by_invoice_id,
            )
            return self._save_artifact(
                task_id=task.id,
                filename=export.filename,
                content_type="text/csv",
                content=render_missing_materials_csv(export).encode("utf-8"),
            )

        if export_job.kind is ExportArtifactKind.FINANCE_DRAFT:
            export = build_finance_draft_export(
                task,
                actor_id=export_job.requested_by,
                format=export_job.format,
                invoices=invoices,
                materials_by_id=materials_by_id,
                validations_by_invoice_id=validations_by_invoice_id,
                splits_by_invoice_id=splits_by_invoice_id,
            )
            return self._save_artifact(
                task_id=task.id,
                filename=export.filename,
                content_type="application/json",
                content=json.dumps(
                    export.model_dump(mode="json"),
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8"),
            )

        raise TaskExportFormatNotImplementedError(
            export_job.kind,
            export_job.format,
        )

    def _save_artifact(
        self,
        *,
        task_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> StoredExportArtifactRecord:
        stored = self._material_file_storage.save(
            task_id=f"{task_id}/_exports",
            original_filename=filename,
            content_type=content_type,
            content=content,
        )
        return StoredExportArtifactRecord(
            storage_key=stored.storage_key,
            filename=stored.original_filename,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
        )
