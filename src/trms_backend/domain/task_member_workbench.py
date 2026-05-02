from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from trms_backend.application.supporting_material_auto_link import SupportingMaterialAutoLinkService
from trms_backend.domain.confirmations import ConfirmationRecord
from trms_backend.domain.expense_details import ExpenseDetailItem
from trms_backend.domain.invoices import InvoiceRecord, ValidationResult, ValidationStatus
from trms_backend.domain.materials import MaterialRecord, MaterialType
from trms_backend.domain.missing_materials import MissingMaterialItem
from trms_backend.domain.recognitions import (
    RecognitionFailureDetail,
    RecognitionFieldCorrectionRecord,
    RecognitionFieldResult,
    RecognitionTaskRecord,
    RecognitionTaskStatus,
)
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.task_member_status import (
    MEMBER_SUBMISSION_IGNORED_RULE_CODES,
    TaskMemberMaterialStatusItem,
    TaskMemberStatusActorNotAllowedError,
    TaskMemberStatusReport,
    build_task_member_status_report,
)
from trms_backend.domain.task_shared_invoices import (
    TaskSharedInvoiceItem,
    build_task_shared_invoice_report,
)
from trms_backend.domain.task_supporting_material_linkage import (
    PendingSupportingMaterialLinkageItem,
    build_pending_supporting_material_candidate_invoice_summary,
    build_task_supporting_material_linkage_report,
)
from trms_backend.domain.tasks import ReimbursementTask


class TaskMemberWorkbenchActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to view member workbench summary for this task")


class TaskMemberWorkbenchQueueGroup(StrEnum):
    READY = "ready"
    RECOGNITION_PENDING = "recognition_pending"
    RECOGNITION_REVIEW = "recognition_review"
    SUPPORTING_MATERIAL_LINKAGE = "supporting_material_linkage"
    MISSING_MATERIALS = "missing_materials"
    SPLIT_INCOMPLETE = "split_incomplete"
    CONFIRMATION_INCOMPLETE = "confirmation_incomplete"


class TaskMemberWorkbenchBlockingReason(StrEnum):
    RECOGNITION_PENDING = "recognition_pending"
    RECOGNITION_REVIEW = "recognition_review"
    SUPPORTING_MATERIAL_LINKAGE = "supporting_material_linkage"
    MISSING_MATERIALS = "missing_materials"
    SPLIT_INCOMPLETE = "split_incomplete"
    CONFIRMATION_INCOMPLETE = "confirmation_incomplete"


class TaskMemberWorkbenchRecognitionItem(BaseModel):
    id: str
    material_id: str
    status: RecognitionTaskStatus
    failure: RecognitionFailureDetail | None = None
    recognized_fields: dict[str, RecognitionFieldResult] = Field(default_factory=dict)
    manual_corrections: list[RecognitionFieldCorrectionRecord] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task_record(
        cls,
        record: RecognitionTaskRecord,
    ) -> "TaskMemberWorkbenchRecognitionItem":
        return cls.model_validate(
            {
                "id": record.id,
                "material_id": record.material_id,
                "status": record.status,
                "failure": record.failure,
                "recognized_fields": record.recognized_fields,
                "manual_corrections": record.manual_corrections,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }
        )


class TaskMemberWorkbenchItem(BaseModel):
    material: TaskMemberMaterialStatusItem
    invoice: InvoiceRecord | None = None
    recognition: TaskMemberWorkbenchRecognitionItem | None = None
    validations: list[ValidationResult] = Field(default_factory=list)
    supporting_materials: list[MaterialRecord] = Field(default_factory=list)
    splits: list[ExpenseSplitRecord] = Field(default_factory=list)
    confirmations: list[ConfirmationRecord] = Field(default_factory=list)
    related_expense_details: list[ExpenseDetailItem] = Field(default_factory=list)
    missing_materials: list[MissingMaterialItem] = Field(default_factory=list)
    queue_group: TaskMemberWorkbenchQueueGroup
    blocking_reasons: list[TaskMemberWorkbenchBlockingReason] = Field(default_factory=list)
    ready_for_submission: bool


class TaskMemberWorkbenchSummary(BaseModel):
    task_id: str
    actor_id: str
    report: TaskMemberStatusReport
    items: list[TaskMemberWorkbenchItem] = Field(default_factory=list)
    pending_supporting_material_linkage_items: list[PendingSupportingMaterialLinkageItem] = (
        Field(default_factory=list)
    )
    shared_invoices: list[TaskSharedInvoiceItem] = Field(default_factory=list)


def build_task_member_workbench_summary(
    task: ReimbursementTask,
    *,
    actor_id: str,
    materials: list[MaterialRecord],
    invoices: list[InvoiceRecord],
    latest_recognitions_by_material_id: dict[str, RecognitionTaskRecord | None],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
    supporting_materials_by_invoice_id: dict[str, list[MaterialRecord]],
    shared_supporting_materials_by_invoice_id: dict[str, list[MaterialRecord]],
    linked_invoice_ids_by_material_id: dict[str, list[str]],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_invoice_id: dict[str, list[ConfirmationRecord]],
    current_confirmations_by_split_id: dict[str, ConfirmationRecord],
    supporting_material_auto_link_service: SupportingMaterialAutoLinkService,
) -> TaskMemberWorkbenchSummary:
    try:
        report = build_task_member_status_report(
            task,
            actor_id=actor_id,
            materials=materials,
            invoices=invoices,
            latest_recognitions_by_material_id=latest_recognitions_by_material_id,
            validations_by_invoice_id=validations_by_invoice_id,
            splits_by_invoice_id=splits_by_invoice_id,
            confirmations_by_split_id=current_confirmations_by_split_id,
        )
    except TaskMemberStatusActorNotAllowedError as error:
        raise TaskMemberWorkbenchActorNotAllowedError() from error

    materials_by_id = {material.id: material for material in materials}
    pending_supporting_material_linkage_report = build_task_supporting_material_linkage_report(
        task,
        actor_id=actor_id,
        include_all_members=False,
        materials=materials,
        invoices=invoices,
        materials_by_id=materials_by_id,
        linked_invoice_ids_by_material_id=linked_invoice_ids_by_material_id,
        supporting_material_auto_link_service=supporting_material_auto_link_service,
    )
    pending_linkage_items_by_material_id = {
        item.material_id: item
        for item in pending_supporting_material_linkage_report.items
    }
    supplemental_linkage_items: list[PendingSupportingMaterialLinkageItem] = []
    shared_invoice_report = build_task_shared_invoice_report(
        task,
        actor_id=actor_id,
        invoices=invoices,
        materials_by_id=materials_by_id,
        validations_by_invoice_id=validations_by_invoice_id,
        supporting_materials_by_invoice_id=shared_supporting_materials_by_invoice_id,
        splits_by_invoice_id=splits_by_invoice_id,
    )

    invoices_by_material_id = {
        invoice.material_id: invoice
        for invoice in invoices
    }
    items: list[TaskMemberWorkbenchItem] = []
    for material in sorted(report.materials, key=lambda item: (item.created_at, item.material_id), reverse=True):
        invoice = invoices_by_material_id.get(material.material_id)
        missing_materials = (
            [entry for entry in report.missing_materials if entry.invoice_id == invoice.id]
            if invoice is not None
            else []
        )
        splits = splits_by_invoice_id.get(invoice.id, []) if invoice is not None else []
        confirmations = confirmations_by_invoice_id.get(invoice.id, []) if invoice is not None else []
        pending_linkage_item = pending_linkage_items_by_material_id.get(material.material_id)
        if pending_linkage_item is None and material.material_type is not MaterialType.INVOICE:
            linked_invoice_ids = linked_invoice_ids_by_material_id.get(material.material_id, [])
            if linked_invoice_ids:
                linked_invoices = [
                    invoice_candidate
                    for invoice_candidate in invoices
                    if invoice_candidate.id in linked_invoice_ids
                ]
                pending_linkage_item = PendingSupportingMaterialLinkageItem(
                    material_id=material.material_id,
                    submitter_id=material.submitter_id,
                    material_type=material.material_type,
                    original_filename=material.original_filename,
                    pending_reason="manual_confirmation_required",
                    linked_invoices=[
                        build_pending_supporting_material_candidate_invoice_summary(
                            invoice_candidate,
                            materials_by_id=materials_by_id,
                        )
                        for invoice_candidate in linked_invoices
                    ],
                    candidate_invoices=[],
                    created_at=material.created_at,
                )
                supplemental_linkage_items.append(pending_linkage_item)
        blocking_reasons = _collect_blocking_reasons(
            material=material,
            invoice=invoice,
            validations=validations_by_invoice_id.get(invoice.id, []) if invoice is not None else [],
            missing_materials=missing_materials,
            splits=splits,
            confirmations=confirmations,
        )
        items.append(
            TaskMemberWorkbenchItem(
                material=material,
                invoice=invoice,
                recognition=(
                    TaskMemberWorkbenchRecognitionItem.from_task_record(
                        latest_recognitions_by_material_id[material.material_id]
                    )
                    if latest_recognitions_by_material_id.get(material.material_id) is not None
                    else None
                ),
                validations=validations_by_invoice_id.get(invoice.id, []) if invoice is not None else [],
                supporting_materials=(
                    supporting_materials_by_invoice_id.get(invoice.id, [])
                    if invoice is not None
                    else []
                ),
                splits=splits,
                confirmations=confirmations,
                related_expense_details=[
                    detail
                    for detail in report.expense_details
                    if detail.invoice.material_id == material.material_id
                ],
                missing_materials=missing_materials,
                queue_group=_resolve_queue_group(blocking_reasons),
                blocking_reasons=blocking_reasons,
                ready_for_submission=len(blocking_reasons) == 0,
            )
        )

    return TaskMemberWorkbenchSummary(
        task_id=task.id,
        actor_id=actor_id.strip(),
        report=report,
        items=items,
        pending_supporting_material_linkage_items=[
            *pending_supporting_material_linkage_report.items,
            *supplemental_linkage_items,
        ],
        shared_invoices=shared_invoice_report.items,
    )


def _collect_blocking_reasons(
    *,
    material: TaskMemberMaterialStatusItem,
    invoice: InvoiceRecord | None,
    validations: list[ValidationResult],
    missing_materials: list[MissingMaterialItem],
    splits: list[ExpenseSplitRecord],
    confirmations: list[ConfirmationRecord],
) -> list[TaskMemberWorkbenchBlockingReason]:
    reasons: list[TaskMemberWorkbenchBlockingReason] = []
    is_invoice_material = material.material_type is MaterialType.INVOICE
    filtered_validations = [
        validation
        for validation in validations
        if validation.rule_code not in MEMBER_SUBMISSION_IGNORED_RULE_CODES
    ]

    if material.recognition_status is RecognitionTaskStatus.PENDING and is_invoice_material:
        reasons.append(TaskMemberWorkbenchBlockingReason.RECOGNITION_PENDING)
    if material.recognition_status is RecognitionTaskStatus.FAILED:
        reasons.append(TaskMemberWorkbenchBlockingReason.RECOGNITION_REVIEW)
    if material.recognition_status is RecognitionTaskStatus.NEEDS_CONFIRMATION and is_invoice_material:
        reasons.append(TaskMemberWorkbenchBlockingReason.RECOGNITION_REVIEW)
    if invoice is None and is_invoice_material:
        reasons.append(TaskMemberWorkbenchBlockingReason.RECOGNITION_REVIEW)
    if missing_materials:
        reasons.append(TaskMemberWorkbenchBlockingReason.MISSING_MATERIALS)
    if _has_split_coverage_gap(invoice=invoice, splits=splits):
        reasons.append(TaskMemberWorkbenchBlockingReason.SPLIT_INCOMPLETE)
    if _has_confirmation_gap(invoice=invoice, splits=splits, confirmations=confirmations):
        reasons.append(TaskMemberWorkbenchBlockingReason.CONFIRMATION_INCOMPLETE)
    if (
        not reasons
        and any(
            validation.status in {ValidationStatus.FAILED, ValidationStatus.PENDING}
            for validation in filtered_validations
        )
    ):
        reasons.append(TaskMemberWorkbenchBlockingReason.RECOGNITION_REVIEW)

    return reasons


def _resolve_queue_group(
    blocking_reasons: list[TaskMemberWorkbenchBlockingReason],
) -> TaskMemberWorkbenchQueueGroup:
    if not blocking_reasons:
        return TaskMemberWorkbenchQueueGroup.READY
    return TaskMemberWorkbenchQueueGroup(blocking_reasons[0].value)


def _has_split_coverage_gap(
    *,
    invoice: InvoiceRecord | None,
    splits: list[ExpenseSplitRecord],
) -> bool:
    if invoice is None or not splits:
        return False
    return sum(split.amount_cents for split in splits) != invoice.amount_cents


def _has_confirmation_gap(
    *,
    invoice: InvoiceRecord | None,
    splits: list[ExpenseSplitRecord],
    confirmations: list[ConfirmationRecord],
) -> bool:
    if invoice is None or not splits:
        return False
    current_confirmations_by_split_id = {
        confirmation.split_id: confirmation
        for confirmation in confirmations
        if confirmation.is_current
    }
    return any(
        current_confirmations_by_split_id.get(split.id) is None
        or current_confirmations_by_split_id[split.id].status.value != "confirmed"
        for split in splits
    )
