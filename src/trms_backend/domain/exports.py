from __future__ import annotations

import csv
from io import StringIO
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field, field_validator, model_validator

from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.invoices import ExpenseType, InvoiceRecord
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.tasks import ReimbursementTask, TaskStatus


class ExportArtifactKind(StrEnum):
    REIMBURSEMENT_SUMMARY = "reimbursement_summary"
    MEMBER_DETAILS = "member_details"
    INVOICE_DETAILS = "invoice_details"
    MISSING_MATERIALS = "missing_materials"
    FINANCE_DRAFT = "finance_draft"
    MERGED_PDF = "merged_pdf"


class ExportArtifactFormat(StrEnum):
    XLSX = "xlsx"
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"


class TaskExportCapability(BaseModel):
    kind: ExportArtifactKind
    formats: list[ExportArtifactFormat] = Field(min_length=1)
    implemented: bool = False
    implemented_formats: list[ExportArtifactFormat] = Field(default_factory=list)


class TaskExportBoundary(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    current_task_status: TaskStatus
    export_allowed: bool
    blocking_reasons: list[str]
    execution_mode: str = Field(default="async_placeholder")
    supported_exports: list[TaskExportCapability]
    note: str = Field(
        default=(
            "reimbursement summary/member details CSV export is available; export jobs and other persisted "
            "artifacts remain placeholders"
        )
    )


class TaskExportJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TaskExportJobRequest(BaseModel):
    actor_id: str = Field(min_length=1)
    kind: ExportArtifactKind
    format: ExportArtifactFormat
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_and_validate(self) -> TaskExportJobRequest:
        self.actor_id = self.actor_id.strip()
        _ensure_export_format_supported(self.kind, self.format)
        return self


class TaskExportJobCreate(BaseModel):
    requested_by: str = Field(min_length=1)
    kind: ExportArtifactKind
    format: ExportArtifactFormat
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_and_validate(self) -> TaskExportJobCreate:
        self.requested_by = self.requested_by.strip()
        _ensure_export_format_supported(self.kind, self.format)
        return self


class TaskExportJobRecord(BaseModel):
    id: str
    task_id: str
    requested_by: str
    kind: ExportArtifactKind
    format: ExportArtifactFormat
    status: TaskExportJobStatus
    parameters: dict[str, Any]
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TaskExportJobStatusUpdate(BaseModel):
    actor_id: str = Field(min_length=1)
    target_status: TaskExportJobStatus
    failure_reason: str | None = None

    @field_validator("failure_reason")
    @classmethod
    def normalize_failure_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("failure_reason must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_failure_reason(self) -> TaskExportJobStatusUpdate:
        self.actor_id = self.actor_id.strip()
        if self.target_status is TaskExportJobStatus.FAILED:
            if self.failure_reason is None:
                raise ValueError("failed export job requires failure_reason")
        elif self.failure_reason is not None:
            raise ValueError("failure_reason is only allowed when target_status is failed")
        return self


class TaskExportActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to manage exports for this task")


class TaskExportJobNotReadyError(ValueError):
    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__("task is not ready for export: " + "; ".join(reasons))


class TaskExportFormatNotSupportedError(ValueError):
    def __init__(
        self,
        kind: ExportArtifactKind,
        format: ExportArtifactFormat,
    ) -> None:
        super().__init__(f"export format {format.value} is not supported for {kind.value}")


class TaskExportJobStatusTransitionError(ValueError):
    def __init__(
        self,
        current_status: TaskExportJobStatus,
        target_status: TaskExportJobStatus,
    ) -> None:
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            "export job cannot transition from "
            f"{current_status.value} to {target_status.value}"
        )


class TaskExportFormatNotImplementedError(ValueError):
    def __init__(
        self,
        kind: ExportArtifactKind,
        format: ExportArtifactFormat,
    ) -> None:
        super().__init__(
            f"export format {format.value} is not implemented yet for {kind.value}"
        )


class ReimbursementSummaryRow(BaseModel):
    expense_type: ExpenseType
    total_amount_cents: int = Field(ge=0)
    member_amounts_cents: dict[str, int]


class ReimbursementSummaryExport(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    format: ExportArtifactFormat
    filename: str
    generated_at: datetime
    member_ids: list[str]
    rows: list[ReimbursementSummaryRow]
    grand_total_amount_cents: int = Field(ge=0)
    grand_total_amounts_cents_by_member: dict[str, int]


class MemberDetailRow(BaseModel):
    member_id: str
    expense_type: ExpenseType
    invoice_number: str
    invoice_amount_cents: int = Field(ge=0)
    split_amount_cents: int = Field(ge=0)
    split_version: int = Field(ge=1)
    confirmation_status: ConfirmationStatus | None = None
    split_note: str | None = None


class MemberDetailsExport(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    format: ExportArtifactFormat
    filename: str
    generated_at: datetime
    rows: list[MemberDetailRow]
    grand_total_amount_cents: int = Field(ge=0)


class TaskExportJobRepository(Protocol):
    def create(
        self,
        *,
        task_id: str,
        data: TaskExportJobCreate,
    ) -> TaskExportJobRecord:
        raise NotImplementedError

    def get(self, export_job_id: str) -> TaskExportJobRecord | None:
        raise NotImplementedError

    def list_by_task(self, task_id: str) -> list[TaskExportJobRecord]:
        raise NotImplementedError

    def update_status(
        self,
        export_job_id: str,
        *,
        target_status: TaskExportJobStatus,
        failure_reason: str | None = None,
    ) -> TaskExportJobRecord | None:
        raise NotImplementedError


def build_task_export_boundary(
    task: ReimbursementTask,
    *,
    actor_id: str,
) -> TaskExportBoundary:
    normalized_actor_id = ensure_task_export_administrator(task, actor_id=actor_id)

    blocking_reasons: list[str] = []
    if task.status not in {TaskStatus.READY_TO_EXPORT, TaskStatus.COMPLETED}:
        blocking_reasons.append(
            "task must be ready_to_export or completed before real exports can be generated"
        )

    return TaskExportBoundary(
        task_id=task.id,
        administrator_id=normalized_actor_id,
        current_task_status=task.status,
        export_allowed=not blocking_reasons,
        blocking_reasons=blocking_reasons,
        supported_exports=_SUPPORTED_EXPORT_CAPABILITIES,
    )


def ensure_task_export_administrator(
    task: ReimbursementTask,
    *,
    actor_id: str,
) -> str:
    normalized_actor_id = actor_id.strip()
    if normalized_actor_id != task.administrator_id:
        raise TaskExportActorNotAllowedError()
    return normalized_actor_id


def create_task_export_job(
    task: ReimbursementTask,
    *,
    payload: TaskExportJobRequest,
    repository: TaskExportJobRepository,
) -> TaskExportJobRecord:
    boundary = build_task_export_boundary(task, actor_id=payload.actor_id)
    if not boundary.export_allowed:
        raise TaskExportJobNotReadyError(boundary.blocking_reasons)

    return repository.create(
        task_id=task.id,
        data=TaskExportJobCreate(
            requested_by=boundary.administrator_id,
            kind=payload.kind,
            format=payload.format,
            parameters=payload.parameters,
        ),
    )


def list_task_export_jobs(
    task: ReimbursementTask,
    *,
    actor_id: str,
    repository: TaskExportJobRepository,
) -> list[TaskExportJobRecord]:
    ensure_task_export_administrator(task, actor_id=actor_id)
    return repository.list_by_task(task.id)


def build_reimbursement_summary_export(
    task: ReimbursementTask,
    *,
    actor_id: str,
    format: ExportArtifactFormat,
    invoices: list[InvoiceRecord],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    generated_at: datetime | None = None,
) -> ReimbursementSummaryExport:
    boundary = build_task_export_boundary(task, actor_id=actor_id)
    if not boundary.export_allowed:
        raise TaskExportJobNotReadyError(boundary.blocking_reasons)
    ensure_export_format_implemented(
        ExportArtifactKind.REIMBURSEMENT_SUMMARY,
        format,
    )

    member_ids = list(task.member_ids)
    member_totals = {member_id: 0 for member_id in member_ids}
    row_totals_by_expense_type = {
        ExpenseType(expense_type): {member_id: 0 for member_id in member_ids}
        for expense_type in task.fee_categories
    }

    for invoice in invoices:
        if invoice.task_id != task.id:
            continue
        row_totals = row_totals_by_expense_type.setdefault(
            invoice.expense_type,
            {member_id: 0 for member_id in member_ids},
        )
        for split in splits_by_invoice_id.get(invoice.id, []):
            if split.member_id not in row_totals:
                row_totals[split.member_id] = 0
            if split.member_id not in member_totals:
                member_totals[split.member_id] = 0
            row_totals[split.member_id] += split.amount_cents
            member_totals[split.member_id] += split.amount_cents

    rows: list[ReimbursementSummaryRow] = []
    ordered_expense_types = list(row_totals_by_expense_type)
    for expense_type in ordered_expense_types:
        member_amounts_cents = row_totals_by_expense_type[expense_type]
        rows.append(
            ReimbursementSummaryRow(
                expense_type=expense_type,
                total_amount_cents=sum(member_amounts_cents.values()),
                member_amounts_cents=dict(member_amounts_cents),
            )
        )

    generated_at = generated_at or datetime.now(timezone.utc)
    return ReimbursementSummaryExport(
        task_id=task.id,
        administrator_id=boundary.administrator_id,
        format=format,
        filename=f"{task.id}-reimbursement-summary.{format.value}",
        generated_at=generated_at,
        member_ids=member_ids,
        rows=rows,
        grand_total_amount_cents=sum(member_totals.values()),
        grand_total_amounts_cents_by_member=member_totals,
    )


def render_reimbursement_summary_csv(export: ReimbursementSummaryExport) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["expense_type", "total_amount_cents", *export.member_ids])
    for row in export.rows:
        writer.writerow(
            [
                row.expense_type.value,
                row.total_amount_cents,
                *[row.member_amounts_cents.get(member_id, 0) for member_id in export.member_ids],
            ]
        )
    writer.writerow(
        [
            "grand_total",
            export.grand_total_amount_cents,
            *[
                export.grand_total_amounts_cents_by_member.get(member_id, 0)
                for member_id in export.member_ids
            ],
        ]
    )
    return buffer.getvalue()


def build_member_details_export(
    task: ReimbursementTask,
    *,
    actor_id: str,
    format: ExportArtifactFormat,
    invoices: list[InvoiceRecord],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
    generated_at: datetime | None = None,
) -> MemberDetailsExport:
    boundary = build_task_export_boundary(task, actor_id=actor_id)
    if not boundary.export_allowed:
        raise TaskExportJobNotReadyError(boundary.blocking_reasons)
    ensure_export_format_implemented(
        ExportArtifactKind.MEMBER_DETAILS,
        format,
    )

    rows: list[MemberDetailRow] = []
    for invoice in invoices:
        current_splits = sorted(
            splits_by_invoice_id.get(invoice.id, []),
            key=lambda split: (split.member_id, split.created_at, split.id),
        )
        for split in current_splits:
            confirmation = confirmations_by_split_id.get(split.id)
            rows.append(
                MemberDetailRow(
                    member_id=split.member_id,
                    expense_type=invoice.expense_type,
                    invoice_number=invoice.invoice_number,
                    invoice_amount_cents=invoice.amount_cents,
                    split_amount_cents=split.amount_cents,
                    split_version=split.version,
                    confirmation_status=(
                        confirmation.status if confirmation is not None else None
                    ),
                    split_note=split.note,
                )
            )

    rows.sort(
        key=lambda row: (
            row.member_id,
            row.expense_type.value,
            row.invoice_number,
        )
    )

    generated_at = generated_at or datetime.now(timezone.utc)
    return MemberDetailsExport(
        task_id=task.id,
        administrator_id=boundary.administrator_id,
        format=format,
        filename=f"{task.id}-member-details.{format.value}",
        generated_at=generated_at,
        rows=rows,
        grand_total_amount_cents=sum(row.split_amount_cents for row in rows),
    )


def render_member_details_csv(export: MemberDetailsExport) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "member_id",
            "expense_type",
            "invoice_number",
            "invoice_amount_cents",
            "split_amount_cents",
            "split_version",
            "confirmation_status",
            "split_note",
        ]
    )
    for row in export.rows:
        writer.writerow(
            [
                row.member_id,
                row.expense_type.value,
                row.invoice_number,
                row.invoice_amount_cents,
                row.split_amount_cents,
                row.split_version,
                row.confirmation_status.value if row.confirmation_status is not None else "",
                row.split_note or "",
            ]
        )
    writer.writerow(
        [
            "grand_total",
            "",
            "",
            "",
            export.grand_total_amount_cents,
            "",
            "",
            "",
        ]
    )
    return buffer.getvalue()


def update_task_export_job_status(
    task: ReimbursementTask,
    *,
    export_job: TaskExportJobRecord,
    payload: TaskExportJobStatusUpdate,
    repository: TaskExportJobRepository,
) -> TaskExportJobRecord:
    ensure_task_export_administrator(task, actor_id=payload.actor_id)
    ensure_task_export_job_can_transition(export_job.status, payload.target_status)
    updated = repository.update_status(
        export_job.id,
        target_status=payload.target_status,
        failure_reason=payload.failure_reason,
    )
    if updated is None:
        raise ValueError("export job not found")
    return updated


def ensure_task_export_job_can_transition(
    current_status: TaskExportJobStatus,
    target_status: TaskExportJobStatus,
) -> None:
    if target_status not in _ALLOWED_EXPORT_JOB_TRANSITIONS[current_status]:
        raise TaskExportJobStatusTransitionError(current_status, target_status)


def _ensure_export_format_supported(
    kind: ExportArtifactKind,
    format: ExportArtifactFormat,
) -> None:
    supported_formats = _SUPPORTED_EXPORT_FORMATS_BY_KIND[kind]
    if format not in supported_formats:
        raise TaskExportFormatNotSupportedError(kind, format)


def ensure_export_format_implemented(
    kind: ExportArtifactKind,
    format: ExportArtifactFormat,
) -> None:
    implemented_formats = _IMPLEMENTED_EXPORT_FORMATS_BY_KIND[kind]
    if format not in implemented_formats:
        raise TaskExportFormatNotImplementedError(kind, format)


_SUPPORTED_EXPORT_CAPABILITIES = [
    TaskExportCapability(
        kind=ExportArtifactKind.REIMBURSEMENT_SUMMARY,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.CSV],
        implemented=True,
        implemented_formats=[ExportArtifactFormat.CSV],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.MEMBER_DETAILS,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.CSV],
        implemented=True,
        implemented_formats=[ExportArtifactFormat.CSV],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.INVOICE_DETAILS,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.CSV],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.MISSING_MATERIALS,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.CSV],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.FINANCE_DRAFT,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.JSON],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.MERGED_PDF,
        formats=[ExportArtifactFormat.PDF],
    ),
]

_SUPPORTED_EXPORT_FORMATS_BY_KIND = {
    capability.kind: set(capability.formats) for capability in _SUPPORTED_EXPORT_CAPABILITIES
}

_IMPLEMENTED_EXPORT_FORMATS_BY_KIND = {
    capability.kind: set(capability.implemented_formats)
    for capability in _SUPPORTED_EXPORT_CAPABILITIES
}

_ALLOWED_EXPORT_JOB_TRANSITIONS: dict[
    TaskExportJobStatus,
    set[TaskExportJobStatus],
] = {
    TaskExportJobStatus.PENDING: {
        TaskExportJobStatus.RUNNING,
        TaskExportJobStatus.SUCCEEDED,
        TaskExportJobStatus.FAILED,
    },
    TaskExportJobStatus.RUNNING: {
        TaskExportJobStatus.SUCCEEDED,
        TaskExportJobStatus.FAILED,
    },
    TaskExportJobStatus.SUCCEEDED: set(),
    TaskExportJobStatus.FAILED: set(),
}
