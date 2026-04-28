from __future__ import annotations

import csv
import hashlib
import json
from io import BytesIO, StringIO
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any, Protocol

from pypdf import PdfReader
from pydantic import BaseModel, Field, field_validator, model_validator

from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.invoices import ExpenseType, InvoiceRecord, ValidationResult, ValidationStatus
from trms_backend.domain.materials import MaterialRecord, MaterialType
from trms_backend.domain.missing_materials import aggregate_task_missing_materials
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
    execution_mode: str = Field(default="async_worker")
    supported_exports: list[TaskExportCapability]
    note: str = Field(
        default=(
            "reimbursement summary/member details/invoice details/missing materials CSV export and "
            "finance draft JSON export are available through async export jobs with persisted "
            "artifacts; merged PDF planning/validation remains a placeholder"
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
    task_status_at_request: TaskStatus | None = None
    task_data_version: str | None = Field(default=None, min_length=64, max_length=64)

    @model_validator(mode="after")
    def normalize_and_validate(self) -> TaskExportJobCreate:
        self.requested_by = self.requested_by.strip()
        _ensure_export_format_supported(self.kind, self.format)
        return self


class ExportArtifactRecord(BaseModel):
    filename: str = Field(min_length=1)
    content_type: str | None = None
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)


class StoredExportArtifactRecord(ExportArtifactRecord):
    storage_key: str = Field(min_length=1)


class TaskExportJobRecord(BaseModel):
    id: str
    task_id: str
    requested_by: str
    kind: ExportArtifactKind
    format: ExportArtifactFormat
    status: TaskExportJobStatus
    parameters: dict[str, Any]
    task_status_at_request: TaskStatus | None = None
    task_data_version: str | None = Field(default=None, min_length=64, max_length=64)
    is_latest_for_task: bool | None = None
    retry_count: int | None = Field(default=None, ge=0)
    artifact: ExportArtifactRecord | None = None
    artifact_storage_key: str | None = Field(default=None, exclude=True)
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


class MergedPdfSourceMaterialError(ValueError):
    def __init__(self, material_id: str, reason: str) -> None:
        self.material_id = material_id
        super().__init__(f"merged pdf source material {material_id} {reason}")


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


class InvoiceDetailRow(BaseModel):
    invoice_number: str
    amount_cents: int = Field(ge=0)
    expense_type: ExpenseType
    submitter_id: str | None = None
    validation_status: ValidationStatus
    failed_rule_codes: list[str] = Field(default_factory=list)
    pending_rule_codes: list[str] = Field(default_factory=list)
    abnormal_validation_messages: list[str] = Field(default_factory=list)


class InvoiceDetailsExport(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    format: ExportArtifactFormat
    filename: str
    generated_at: datetime
    rows: list[InvoiceDetailRow]


class MissingMaterialExportRow(BaseModel):
    member_id: str | None = None
    expense_type: ExpenseType
    invoice_number: str
    required_material_type: MaterialType
    source_rule_code: str
    message: str


class MissingMaterialsExport(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    format: ExportArtifactFormat
    filename: str
    generated_at: datetime
    rows: list[MissingMaterialExportRow]


class FinanceDraftSplitRow(BaseModel):
    member_id: str
    amount_cents: int = Field(ge=0)
    split_version: int = Field(ge=1)
    split_note: str | None = None


class FinanceDraftInvoiceRow(BaseModel):
    invoice_number: str
    expense_type: ExpenseType
    amount_cents: int = Field(ge=0)
    buyer_name: str
    tax_number: str
    seller_name: str | None = None
    issue_date: date | None = None
    transaction_time: datetime | None = None
    submitter_id: str | None = None
    validation_status: ValidationStatus
    failed_rule_codes: list[str] = Field(default_factory=list)
    pending_rule_codes: list[str] = Field(default_factory=list)
    split_items: list[FinanceDraftSplitRow] = Field(default_factory=list)


class FinanceDraftExport(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    format: ExportArtifactFormat
    filename: str
    generated_at: datetime
    competition_name: str
    competition_location: str
    competition_start_date: date
    competition_end_date: date
    project_info: str
    reimburser_info: str
    invoice_title: str
    tax_number: str
    total_amount_cents: int = Field(ge=0)
    invoice_count: int = Field(ge=0)
    expense_totals_cents: dict[str, int]
    member_totals_cents: dict[str, int]
    invoice_rows: list[FinanceDraftInvoiceRow]


class MergedPdfPlanItemKind(StrEnum):
    REIMBURSEMENT_SUMMARY = "reimbursement_summary"
    MEMBER_DETAILS = "member_details"
    INVOICE_DETAILS = "invoice_details"
    INVOICE_MATERIAL = "invoice_material"
    SUPPORTING_MATERIAL = "supporting_material"


class MergedPdfPlanItemStatus(StrEnum):
    PLACEHOLDER = "placeholder"
    READY = "ready"


class MergedPdfPlanItem(BaseModel):
    sequence: int = Field(ge=1)
    kind: MergedPdfPlanItemKind
    status: MergedPdfPlanItemStatus
    label: str
    note: str | None = None
    material_id: str | None = None
    material_type: MaterialType | None = None
    original_filename: str | None = None


class MergedPdfExportPlan(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    format: ExportArtifactFormat
    filename: str
    generated_at: datetime
    ordered_items: list[MergedPdfPlanItem]
    note: str = Field(
        default=(
            "phase-1 merged PDF remains a planning/validation placeholder; "
            "generated summary/detail pages are reserved in order but not rendered yet"
        )
    )


class TaskExportVersionSnapshot(BaseModel):
    task_status: TaskStatus
    task_data_version: str = Field(min_length=64, max_length=64)


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

    def list_pending(self, *, limit: int = 10) -> list[TaskExportJobRecord]:
        raise NotImplementedError

    def update_status(
        self,
        export_job_id: str,
        *,
        target_status: TaskExportJobStatus,
        failure_reason: str | None = None,
        artifact: StoredExportArtifactRecord | None = None,
        expected_current_status: TaskExportJobStatus | None = None,
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
    snapshot: TaskExportVersionSnapshot,
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
            task_status_at_request=snapshot.task_status,
            task_data_version=snapshot.task_data_version,
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


def build_invoice_details_export(
    task: ReimbursementTask,
    *,
    actor_id: str,
    format: ExportArtifactFormat,
    invoices: list[InvoiceRecord],
    materials_by_id: dict[str, MaterialRecord],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
    generated_at: datetime | None = None,
) -> InvoiceDetailsExport:
    boundary = build_task_export_boundary(task, actor_id=actor_id)
    if not boundary.export_allowed:
        raise TaskExportJobNotReadyError(boundary.blocking_reasons)
    ensure_export_format_implemented(
        ExportArtifactKind.INVOICE_DETAILS,
        format,
    )

    rows: list[InvoiceDetailRow] = []
    for invoice in invoices:
        validations = validations_by_invoice_id.get(invoice.id, [])
        material = materials_by_id.get(invoice.material_id)
        rows.append(
            InvoiceDetailRow(
                invoice_number=invoice.invoice_number,
                amount_cents=invoice.amount_cents,
                expense_type=invoice.expense_type,
                submitter_id=material.submitter_id if material is not None else None,
                validation_status=_summarize_invoice_validation_status(validations),
                failed_rule_codes=sorted(
                    {result.rule_code for result in validations if result.status is ValidationStatus.FAILED}
                ),
                pending_rule_codes=sorted(
                    {result.rule_code for result in validations if result.status is ValidationStatus.PENDING}
                ),
                abnormal_validation_messages=[
                    result.message
                    for result in validations
                    if result.status in {ValidationStatus.FAILED, ValidationStatus.PENDING}
                ],
            )
        )

    rows.sort(
        key=lambda row: (
            row.invoice_number,
            row.submitter_id or "",
            row.expense_type.value,
            row.amount_cents,
        )
    )

    generated_at = generated_at or datetime.now(timezone.utc)
    return InvoiceDetailsExport(
        task_id=task.id,
        administrator_id=boundary.administrator_id,
        format=format,
        filename=f"{task.id}-invoice-details.{format.value}",
        generated_at=generated_at,
        rows=rows,
    )


def render_invoice_details_csv(export: InvoiceDetailsExport) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "invoice_number",
            "amount_cents",
            "expense_type",
            "submitter_id",
            "validation_status",
            "failed_rule_codes",
            "pending_rule_codes",
            "abnormal_validation_messages",
        ]
    )
    for row in export.rows:
        writer.writerow(
            [
                row.invoice_number,
                row.amount_cents,
                row.expense_type.value,
                row.submitter_id or "",
                row.validation_status.value,
                ";".join(row.failed_rule_codes),
                ";".join(row.pending_rule_codes),
                " | ".join(row.abnormal_validation_messages),
            ]
        )
    return buffer.getvalue()


def build_missing_materials_export(
    task: ReimbursementTask,
    *,
    actor_id: str,
    format: ExportArtifactFormat,
    invoices: list[InvoiceRecord],
    materials_by_id: dict[str, MaterialRecord],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
    generated_at: datetime | None = None,
) -> MissingMaterialsExport:
    boundary = build_task_export_boundary(task, actor_id=actor_id)
    if not boundary.export_allowed:
        raise TaskExportJobNotReadyError(boundary.blocking_reasons)
    ensure_export_format_implemented(
        ExportArtifactKind.MISSING_MATERIALS,
        format,
    )

    missing_materials = aggregate_task_missing_materials(
        task_id=task.id,
        invoices=invoices,
        materials_by_id=materials_by_id,
        validations_by_invoice_id=validations_by_invoice_id,
    )
    rows = [
        MissingMaterialExportRow(
            member_id=item.member_id,
            expense_type=item.expense_type,
            invoice_number=item.invoice_number,
            required_material_type=item.required_material_type,
            source_rule_code=item.source_rule_code,
            message=item.message,
        )
        for item in missing_materials.items
    ]
    rows.sort(
        key=lambda row: (
            row.member_id or "",
            row.expense_type.value,
            row.invoice_number,
            row.required_material_type.value,
        )
    )

    generated_at = generated_at or datetime.now(timezone.utc)
    return MissingMaterialsExport(
        task_id=task.id,
        administrator_id=boundary.administrator_id,
        format=format,
        filename=f"{task.id}-missing-materials.{format.value}",
        generated_at=generated_at,
        rows=rows,
    )


def render_missing_materials_csv(export: MissingMaterialsExport) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "member_id",
            "expense_type",
            "invoice_number",
            "required_material_type",
            "source_rule_code",
            "message",
        ]
    )
    for row in export.rows:
        writer.writerow(
            [
                row.member_id or "",
                row.expense_type.value,
                row.invoice_number,
                row.required_material_type.value,
                row.source_rule_code,
                row.message,
            ]
        )
    return buffer.getvalue()


def build_finance_draft_export(
    task: ReimbursementTask,
    *,
    actor_id: str,
    format: ExportArtifactFormat,
    invoices: list[InvoiceRecord],
    materials_by_id: dict[str, MaterialRecord],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    generated_at: datetime | None = None,
) -> FinanceDraftExport:
    boundary = build_task_export_boundary(task, actor_id=actor_id)
    if not boundary.export_allowed:
        raise TaskExportJobNotReadyError(boundary.blocking_reasons)
    ensure_export_format_implemented(
        ExportArtifactKind.FINANCE_DRAFT,
        format,
    )

    expense_totals_cents = {expense_type: 0 for expense_type in task.fee_categories}
    member_totals_cents = {member_id: 0 for member_id in task.member_ids}
    invoice_rows: list[FinanceDraftInvoiceRow] = []

    for invoice in invoices:
        if invoice.task_id != task.id:
            continue

        validations = validations_by_invoice_id.get(invoice.id, [])
        material = materials_by_id.get(invoice.material_id)
        split_items: list[FinanceDraftSplitRow] = []
        for split in sorted(
            splits_by_invoice_id.get(invoice.id, []),
            key=lambda item: (item.member_id, item.created_at, item.id),
        ):
            split_items.append(
                FinanceDraftSplitRow(
                    member_id=split.member_id,
                    amount_cents=split.amount_cents,
                    split_version=split.version,
                    split_note=split.note,
                )
            )
            member_totals_cents.setdefault(split.member_id, 0)
            member_totals_cents[split.member_id] += split.amount_cents

        expense_totals_cents.setdefault(invoice.expense_type.value, 0)
        expense_totals_cents[invoice.expense_type.value] += invoice.amount_cents
        invoice_rows.append(
            FinanceDraftInvoiceRow(
                invoice_number=invoice.invoice_number,
                expense_type=invoice.expense_type,
                amount_cents=invoice.amount_cents,
                buyer_name=invoice.buyer_name,
                tax_number=invoice.tax_number,
                seller_name=invoice.seller_name,
                issue_date=invoice.issue_date,
                transaction_time=invoice.transaction_time,
                submitter_id=material.submitter_id if material is not None else None,
                validation_status=_summarize_invoice_validation_status(validations),
                failed_rule_codes=sorted(
                    {result.rule_code for result in validations if result.status is ValidationStatus.FAILED}
                ),
                pending_rule_codes=sorted(
                    {result.rule_code for result in validations if result.status is ValidationStatus.PENDING}
                ),
                split_items=split_items,
            )
        )

    invoice_rows.sort(
        key=lambda row: (
            row.expense_type.value,
            row.invoice_number,
            row.submitter_id or "",
            row.amount_cents,
        )
    )

    generated_at = generated_at or datetime.now(timezone.utc)
    return FinanceDraftExport(
        task_id=task.id,
        administrator_id=boundary.administrator_id,
        format=format,
        filename=f"{task.id}-finance-draft.{format.value}",
        generated_at=generated_at,
        competition_name=task.competition_name,
        competition_location=task.competition_location,
        competition_start_date=task.competition_start_date,
        competition_end_date=task.competition_end_date,
        project_info=task.project_info,
        reimburser_info=task.reimburser_info,
        invoice_title=task.invoice_title,
        tax_number=task.tax_number,
        total_amount_cents=sum(item.amount_cents for item in invoice_rows),
        invoice_count=len(invoice_rows),
        expense_totals_cents=expense_totals_cents,
        member_totals_cents=member_totals_cents,
        invoice_rows=invoice_rows,
    )


def build_merged_pdf_export_plan(
    task: ReimbursementTask,
    *,
    actor_id: str,
    format: ExportArtifactFormat,
    materials: list[MaterialRecord],
    material_bytes_by_id: dict[str, bytes],
    generated_at: datetime | None = None,
) -> MergedPdfExportPlan:
    boundary = build_task_export_boundary(task, actor_id=actor_id)
    if not boundary.export_allowed:
        raise TaskExportJobNotReadyError(boundary.blocking_reasons)
    _ensure_export_format_supported(ExportArtifactKind.MERGED_PDF, format)

    ordered_materials = sorted(
        (
            material
            for material in materials
            if material.task_id == task.id
        ),
        key=lambda material: (
            0 if material.material_type is MaterialType.INVOICE else 1,
            material.created_at,
            material.original_filename,
            material.id,
        ),
    )

    ordered_items = [
        MergedPdfPlanItem(
            sequence=1,
            kind=MergedPdfPlanItemKind.REIMBURSEMENT_SUMMARY,
            status=MergedPdfPlanItemStatus.PLACEHOLDER,
            label="报销汇总表",
            note="当前仅保留合并顺序占位，尚未渲染为 PDF 页面",
        ),
        MergedPdfPlanItem(
            sequence=2,
            kind=MergedPdfPlanItemKind.MEMBER_DETAILS,
            status=MergedPdfPlanItemStatus.PLACEHOLDER,
            label="成员报销明细表",
            note="当前仅保留合并顺序占位，尚未渲染为 PDF 页面",
        ),
        MergedPdfPlanItem(
            sequence=3,
            kind=MergedPdfPlanItemKind.INVOICE_DETAILS,
            status=MergedPdfPlanItemStatus.PLACEHOLDER,
            label="发票明细表",
            note="当前仅保留合并顺序占位，尚未渲染为 PDF 页面",
        ),
    ]

    next_sequence = len(ordered_items) + 1
    for material in ordered_materials:
        _validate_merged_pdf_material(
            material,
            raw_content=material_bytes_by_id.get(material.id),
        )
        ordered_items.append(
            MergedPdfPlanItem(
                sequence=next_sequence,
                kind=(
                    MergedPdfPlanItemKind.INVOICE_MATERIAL
                    if material.material_type is MaterialType.INVOICE
                    else MergedPdfPlanItemKind.SUPPORTING_MATERIAL
                ),
                status=MergedPdfPlanItemStatus.READY,
                label=material.original_filename,
                material_id=material.id,
                material_type=material.material_type,
                original_filename=material.original_filename,
            )
        )
        next_sequence += 1

    generated_at = generated_at or datetime.now(timezone.utc)
    return MergedPdfExportPlan(
        task_id=task.id,
        administrator_id=boundary.administrator_id,
        format=format,
        filename=f"{task.id}-merged-printing.pdf",
        generated_at=generated_at,
        ordered_items=ordered_items,
    )


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


def build_task_export_version_snapshot(
    task: ReimbursementTask,
    *,
    invoices: list[InvoiceRecord],
    materials: list[MaterialRecord],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
) -> TaskExportVersionSnapshot:
    payload = {
        "task": task.model_dump(mode="json"),
        "materials": [
            material.model_dump(mode="json")
            for material in sorted(
                materials,
                key=lambda item: (item.created_at, item.id),
            )
        ],
        "invoices": [
            invoice.model_dump(mode="json")
            for invoice in sorted(
                invoices,
                key=lambda item: (item.created_at, item.id),
            )
        ],
        "validations_by_invoice_id": {
            invoice_id: [
                validation.model_dump(mode="json")
                for validation in sorted(
                    validations,
                    key=lambda item: (item.created_at, item.id),
                )
            ]
            for invoice_id, validations in sorted(validations_by_invoice_id.items())
        },
        "splits_by_invoice_id": {
            invoice_id: [
                split.model_dump(mode="json")
                for split in sorted(
                    splits,
                    key=lambda item: (item.created_at, item.id),
                )
            ]
            for invoice_id, splits in sorted(splits_by_invoice_id.items())
        },
        "confirmations_by_split_id": {
            split_id: confirmation.model_dump(mode="json")
            for split_id, confirmation in sorted(confirmations_by_split_id.items())
        },
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return TaskExportVersionSnapshot(
        task_status=task.status,
        task_data_version=hashlib.sha256(encoded).hexdigest(),
    )


def with_task_export_job_latest_flag(
    export_job: TaskExportJobRecord,
    *,
    snapshot: TaskExportVersionSnapshot,
) -> TaskExportJobRecord:
    return export_job.model_copy(
        update={
            "is_latest_for_task": export_job.task_data_version == snapshot.task_data_version,
        }
    )


def build_task_export_retry_counts(
    export_jobs: list[TaskExportJobRecord],
) -> dict[str, int]:
    retry_counts: dict[str, int] = {}
    attempts_by_signature: dict[str, int] = {}
    for export_job in sorted(export_jobs, key=lambda item: (item.created_at, item.id)):
        signature = json.dumps(
            {
                "kind": export_job.kind.value,
                "format": export_job.format.value,
                "parameters": export_job.parameters,
                "task_data_version": export_job.task_data_version,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        retry_counts[export_job.id] = attempts_by_signature.get(signature, 0)
        attempts_by_signature[signature] = retry_counts[export_job.id] + 1
    return retry_counts


def with_task_export_job_retry_count(
    export_job: TaskExportJobRecord,
    *,
    retry_count: int,
) -> TaskExportJobRecord:
    return export_job.model_copy(update={"retry_count": retry_count})


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
        implemented=True,
        implemented_formats=[ExportArtifactFormat.CSV],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.MISSING_MATERIALS,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.CSV],
        implemented=True,
        implemented_formats=[ExportArtifactFormat.CSV],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.FINANCE_DRAFT,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.JSON],
        implemented=True,
        implemented_formats=[ExportArtifactFormat.JSON],
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


def _summarize_invoice_validation_status(
    validations: list[ValidationResult],
) -> ValidationStatus:
    statuses = {result.status for result in validations}
    if ValidationStatus.FAILED in statuses:
        return ValidationStatus.FAILED
    if ValidationStatus.PENDING in statuses:
        return ValidationStatus.PENDING
    if ValidationStatus.PASSED in statuses:
        return ValidationStatus.PASSED
    return ValidationStatus.NOT_APPLICABLE


def _validate_merged_pdf_material(
    material: MaterialRecord,
    *,
    raw_content: bytes | None,
) -> None:
    if material.content_type != "application/pdf":
        raise MergedPdfSourceMaterialError(
            material.id,
            f"has unsupported content type {material.content_type or '<missing>'}",
        )
    if raw_content is None:
        raise MergedPdfSourceMaterialError(material.id, "file content is missing from storage")

    try:
        reader = PdfReader(BytesIO(raw_content), strict=True)
        if reader.is_encrypted:
            raise MergedPdfSourceMaterialError(material.id, "is encrypted")
        if len(reader.pages) == 0:
            raise MergedPdfSourceMaterialError(material.id, "contains no readable pages")
    except MergedPdfSourceMaterialError:
        raise
    except Exception as error:
        raise MergedPdfSourceMaterialError(
            material.id,
            f"is unreadable: {error}",
        ) from error
