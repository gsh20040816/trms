from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.exports import build_task_export_boundary
from trms_backend.domain.invoices import InvoiceRecord, ValidationResult, ValidationSeverity, ValidationStatus
from trms_backend.domain.materials import MaterialRecord
from trms_backend.domain.missing_materials import (
    aggregate_task_missing_materials,
    is_missing_material_validation_result,
)
from trms_backend.domain.recognitions import RecognitionTaskRecord, RecognitionTaskStatus
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.task_supporting_material_linkage import (
    PendingSupportingMaterialLinkageItem,
    build_task_supporting_material_linkage_report,
)
from trms_backend.domain.tasks import ReimbursementTask, ensure_task_administrator


class TaskReadinessActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to view task readiness for this task")


class TaskReadinessIssueKind(StrEnum):
    RECOGNITION_PENDING = "recognition_pending"
    RECOGNITION_FAILED = "recognition_failed"
    RECOGNITION_NEEDS_CONFIRMATION = "recognition_needs_confirmation"
    SUPPORTING_MATERIAL_LINKAGE = "supporting_material_linkage"
    MISSING_MATERIALS = "missing_materials"
    VALIDATION_BLOCKER = "validation_blocker"
    SPLIT_INCOMPLETE = "split_incomplete"
    MEMBER_CONFIRMATION_PENDING = "member_confirmation_pending"
    MEMBER_CONFIRMATION_DISPUTED = "member_confirmation_disputed"
    EXPORT_BLOCKER = "export_blocker"


class TaskReadinessCounts(BaseModel):
    pending_recognition_count: int = Field(ge=0)
    failed_recognition_count: int = Field(ge=0)
    needs_confirmation_recognition_count: int = Field(ge=0)
    pending_supporting_material_linkage_count: int = Field(ge=0)
    missing_material_count: int = Field(ge=0)
    blocker_validation_count: int = Field(ge=0)
    split_incomplete_count: int = Field(ge=0)
    pending_confirmation_count: int = Field(ge=0)
    disputed_confirmation_count: int = Field(ge=0)
    export_blocking_reason_count: int = Field(ge=0)


class TaskReadinessIssue(BaseModel):
    kind: TaskReadinessIssueKind
    label: str
    count: int = Field(ge=0)
    blocking: bool = True
    invoice_ids: list[str] = Field(default_factory=list)
    material_ids: list[str] = Field(default_factory=list)
    split_ids: list[str] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)


class TaskReadinessSummary(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    ready_for_export: bool
    counts: TaskReadinessCounts
    issues: list[TaskReadinessIssue] = Field(default_factory=list)
    export_blocking_reasons: list[str] = Field(default_factory=list)


def build_task_readiness_summary(
    task: ReimbursementTask,
    *,
    administrator_id: str,
    materials: list[MaterialRecord],
    pending_assignment_materials: list[MaterialRecord],
    latest_recognitions_by_material_id: dict[str, RecognitionTaskRecord | None],
    invoices: list[InvoiceRecord],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
    linked_invoice_ids_by_material_id: dict[str, list[str]],
) -> TaskReadinessSummary:
    normalized_administrator_id = ensure_task_administrator(
        task,
        actor_id=administrator_id,
        error_type=TaskReadinessActorNotAllowedError,
    )

    materials_by_id = {material.id: material for material in materials}
    pending_linkage_report = build_task_supporting_material_linkage_report(
        task,
        actor_id=normalized_administrator_id,
        include_all_members=True,
        materials=materials,
        invoices=invoices,
        materials_by_id=materials_by_id,
        linked_invoice_ids_by_material_id=linked_invoice_ids_by_material_id,
    )
    missing_materials = aggregate_task_missing_materials(
        task_id=task.id,
        invoices=invoices,
        materials_by_id=materials_by_id,
        validations_by_invoice_id=validations_by_invoice_id,
    )
    export_boundary = build_task_export_boundary(task, actor_id=normalized_administrator_id)

    issues: list[TaskReadinessIssue] = []

    pending_recognition_material_ids = _material_ids_by_recognition_status(
        materials,
        latest_recognitions_by_material_id,
        RecognitionTaskStatus.PENDING,
    )
    if pending_recognition_material_ids:
        issues.append(
            TaskReadinessIssue(
                kind=TaskReadinessIssueKind.RECOGNITION_PENDING,
                label="待识别",
                count=len(pending_recognition_material_ids),
                material_ids=pending_recognition_material_ids,
            )
        )

    failed_recognition_material_ids = _material_ids_by_recognition_status(
        materials,
        latest_recognitions_by_material_id,
        RecognitionTaskStatus.FAILED,
    )
    if failed_recognition_material_ids:
        issues.append(
            TaskReadinessIssue(
                kind=TaskReadinessIssueKind.RECOGNITION_FAILED,
                label="识别失败",
                count=len(failed_recognition_material_ids),
                material_ids=failed_recognition_material_ids,
            )
        )

    needs_confirmation_material_ids = _material_ids_by_recognition_status(
        materials,
        latest_recognitions_by_material_id,
        RecognitionTaskStatus.NEEDS_CONFIRMATION,
    )
    if needs_confirmation_material_ids:
        issues.append(
            TaskReadinessIssue(
                kind=TaskReadinessIssueKind.RECOGNITION_NEEDS_CONFIRMATION,
                label="低置信待确认",
                count=len(needs_confirmation_material_ids),
                material_ids=needs_confirmation_material_ids,
            )
        )

    if pending_linkage_report.items:
        issues.append(
            TaskReadinessIssue(
                kind=TaskReadinessIssueKind.SUPPORTING_MATERIAL_LINKAGE,
                label="待关联附件",
                count=len(pending_linkage_report.items),
                material_ids=[item.material_id for item in pending_linkage_report.items],
                invoice_ids=_dedup_invoice_ids_from_linkage_items(pending_linkage_report.items),
            )
        )

    if missing_materials.items:
        issues.append(
            TaskReadinessIssue(
                kind=TaskReadinessIssueKind.MISSING_MATERIALS,
                label="缺失材料",
                count=len(missing_materials.items),
                invoice_ids=[item.invoice_id for item in missing_materials.items],
                details=[item.message for item in missing_materials.items],
            )
        )

    blocker_validations = _collect_non_missing_blocker_validations(validations_by_invoice_id)
    if blocker_validations:
        issues.append(
            TaskReadinessIssue(
                kind=TaskReadinessIssueKind.VALIDATION_BLOCKER,
                label="异常校验",
                count=len(blocker_validations),
                invoice_ids=[validation.target_id for validation in blocker_validations],
                details=[validation.message for validation in blocker_validations],
            )
        )

    split_incomplete_invoice_ids = _collect_split_incomplete_invoice_ids(invoices, splits_by_invoice_id)
    if split_incomplete_invoice_ids:
        issues.append(
            TaskReadinessIssue(
                kind=TaskReadinessIssueKind.SPLIT_INCOMPLETE,
                label="分摊未完成",
                count=len(split_incomplete_invoice_ids),
                invoice_ids=split_incomplete_invoice_ids,
            )
        )

    pending_confirmation_split_ids = _collect_confirmation_split_ids(
        splits_by_invoice_id,
        confirmations_by_split_id,
        target_status=ConfirmationStatus.PENDING,
        include_missing=True,
    )
    if pending_confirmation_split_ids:
        issues.append(
            TaskReadinessIssue(
                kind=TaskReadinessIssueKind.MEMBER_CONFIRMATION_PENDING,
                label="成员未确认",
                count=len(pending_confirmation_split_ids),
                split_ids=pending_confirmation_split_ids,
            )
        )

    disputed_confirmation_split_ids = _collect_confirmation_split_ids(
        splits_by_invoice_id,
        confirmations_by_split_id,
        target_status=ConfirmationStatus.DISPUTED,
        include_missing=False,
    )
    if disputed_confirmation_split_ids:
        issues.append(
            TaskReadinessIssue(
                kind=TaskReadinessIssueKind.MEMBER_CONFIRMATION_DISPUTED,
                label="有异议",
                count=len(disputed_confirmation_split_ids),
                split_ids=disputed_confirmation_split_ids,
            )
        )

    if export_boundary.blocking_reasons:
        issues.append(
            TaskReadinessIssue(
                kind=TaskReadinessIssueKind.EXPORT_BLOCKER,
                label="导出阻塞原因",
                count=len(export_boundary.blocking_reasons),
                details=export_boundary.blocking_reasons,
            )
        )

    return TaskReadinessSummary(
        task_id=task.id,
        administrator_id=normalized_administrator_id,
        ready_for_export=export_boundary.export_allowed,
        counts=TaskReadinessCounts(
            pending_recognition_count=len(pending_recognition_material_ids),
            failed_recognition_count=len(failed_recognition_material_ids),
            needs_confirmation_recognition_count=len(needs_confirmation_material_ids),
            pending_supporting_material_linkage_count=len(pending_linkage_report.items),
            missing_material_count=len(missing_materials.items),
            blocker_validation_count=len(blocker_validations),
            split_incomplete_count=len(split_incomplete_invoice_ids),
            pending_confirmation_count=len(pending_confirmation_split_ids),
            disputed_confirmation_count=len(disputed_confirmation_split_ids),
            export_blocking_reason_count=len(export_boundary.blocking_reasons),
        ),
        issues=issues,
        export_blocking_reasons=export_boundary.blocking_reasons,
    )


def _material_ids_by_recognition_status(
    materials: list[MaterialRecord],
    latest_recognitions_by_material_id: dict[str, RecognitionTaskRecord | None],
    target_status: RecognitionTaskStatus,
) -> list[str]:
    material_ids: list[str] = []
    for material in sorted(materials, key=lambda item: (item.created_at, item.id)):
        recognition = latest_recognitions_by_material_id.get(material.id)
        if recognition is not None and recognition.status is target_status:
            material_ids.append(material.id)
    return material_ids


def _dedup_invoice_ids_from_linkage_items(
    items: list[PendingSupportingMaterialLinkageItem],
) -> list[str]:
    seen: set[str] = set()
    invoice_ids: list[str] = []
    for item in items:
        for candidate in item.candidate_invoices:
            if candidate.invoice_id in seen:
                continue
            seen.add(candidate.invoice_id)
            invoice_ids.append(candidate.invoice_id)
    return invoice_ids


def _collect_non_missing_blocker_validations(
    validations_by_invoice_id: dict[str, list[ValidationResult]],
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for validations in validations_by_invoice_id.values():
        for validation in validations:
            if validation.severity is not ValidationSeverity.BLOCKER:
                continue
            if validation.status not in {ValidationStatus.FAILED, ValidationStatus.PENDING}:
                continue
            if is_missing_material_validation_result(validation):
                continue
            results.append(validation)
    return results


def _collect_split_incomplete_invoice_ids(
    invoices: list[InvoiceRecord],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
) -> list[str]:
    invoice_ids: list[str] = []
    for invoice in invoices:
        splits = splits_by_invoice_id.get(invoice.id, [])
        if not splits:
            invoice_ids.append(invoice.id)
            continue
        total_amount_cents = sum(split.amount_cents for split in splits)
        if total_amount_cents != invoice.amount_cents:
            invoice_ids.append(invoice.id)
    return invoice_ids


def _collect_confirmation_split_ids(
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
    *,
    target_status: ConfirmationStatus,
    include_missing: bool,
) -> list[str]:
    split_ids: list[str] = []
    for splits in splits_by_invoice_id.values():
        for split in splits:
            confirmation = confirmations_by_split_id.get(split.id)
            if confirmation is None:
                if include_missing:
                    split_ids.append(split.id)
                continue
            if confirmation.status is target_status:
                split_ids.append(split.id)
    return split_ids
