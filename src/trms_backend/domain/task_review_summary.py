from __future__ import annotations

from pydantic import BaseModel, Field

from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.invoices import InvoiceRecord, ValidationResult, ValidationSeverity, ValidationStatus
from trms_backend.domain.materials import MaterialRecord
from trms_backend.domain.recognitions import RecognitionTaskRecord, RecognitionTaskStatus
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.tasks import ReimbursementTask


class TaskReviewSummaryActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to view review summary for this task")


class TaskReviewSummaryMaterialItem(BaseModel):
    material: MaterialRecord
    latest_recognition: RecognitionTaskRecord | None
    invoice_id: str | None
    supporting_invoice_ids: list[str]


class TaskReviewSummarySplitItem(BaseModel):
    split: ExpenseSplitRecord
    confirmation: ConfirmationRecord | None


class TaskReviewSummaryInvoiceItem(BaseModel):
    invoice: InvoiceRecord
    supporting_material_ids: list[str]
    validations: list[ValidationResult]
    splits: list[TaskReviewSummarySplitItem]


class TaskReviewSummaryCounts(BaseModel):
    material_count: int = Field(ge=0)
    pending_assignment_material_count: int = Field(ge=0)
    invoice_count: int = Field(ge=0)
    validation_count: int = Field(ge=0)
    blocker_failed_validation_count: int = Field(ge=0)
    split_count: int = Field(ge=0)
    confirmed_split_count: int = Field(ge=0)
    pending_confirmation_count: int = Field(ge=0)
    disputed_confirmation_count: int = Field(ge=0)
    missing_confirmation_count: int = Field(ge=0)
    pending_recognition_count: int = Field(ge=0)
    failed_recognition_count: int = Field(ge=0)
    needs_confirmation_recognition_count: int = Field(ge=0)


class TaskReviewSummary(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    counts: TaskReviewSummaryCounts
    materials: list[TaskReviewSummaryMaterialItem]
    pending_assignment_materials: list[MaterialRecord]
    invoices: list[TaskReviewSummaryInvoiceItem]


def build_task_review_summary(
    task: ReimbursementTask,
    *,
    administrator_id: str,
    materials: list[MaterialRecord],
    pending_assignment_materials: list[MaterialRecord],
    latest_recognitions_by_material_id: dict[str, RecognitionTaskRecord | None],
    invoices: list[InvoiceRecord],
    invoice_by_material_id: dict[str, InvoiceRecord],
    supporting_invoice_ids_by_material_id: dict[str, list[str]],
    supporting_material_ids_by_invoice_id: dict[str, list[str]],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
) -> TaskReviewSummary:
    normalized_administrator_id = administrator_id.strip()
    if normalized_administrator_id != task.administrator_id:
        raise TaskReviewSummaryActorNotAllowedError()

    material_items = [
        TaskReviewSummaryMaterialItem(
            material=material,
            latest_recognition=latest_recognitions_by_material_id.get(material.id),
            invoice_id=(
                invoice_by_material_id[material.id].id
                if material.id in invoice_by_material_id
                else None
            ),
            supporting_invoice_ids=supporting_invoice_ids_by_material_id.get(material.id, []),
        )
        for material in materials
    ]

    invoice_items: list[TaskReviewSummaryInvoiceItem] = []
    confirmed_split_count = 0
    pending_confirmation_count = 0
    disputed_confirmation_count = 0
    missing_confirmation_count = 0
    blocker_failed_validation_count = 0
    validation_count = 0
    split_count = 0
    for invoice in invoices:
        validations = validations_by_invoice_id.get(invoice.id, [])
        validation_count += len(validations)
        blocker_failed_validation_count += sum(
            1
            for result in validations
            if result.severity is ValidationSeverity.BLOCKER and result.status is ValidationStatus.FAILED
        )

        split_items: list[TaskReviewSummarySplitItem] = []
        for split in splits_by_invoice_id.get(invoice.id, []):
            split_count += 1
            confirmation = confirmations_by_split_id.get(split.id)
            if confirmation is None:
                missing_confirmation_count += 1
            elif confirmation.status is ConfirmationStatus.CONFIRMED:
                confirmed_split_count += 1
            elif confirmation.status is ConfirmationStatus.PENDING:
                pending_confirmation_count += 1
            else:
                disputed_confirmation_count += 1

            split_items.append(
                TaskReviewSummarySplitItem(
                    split=split,
                    confirmation=confirmation,
                )
            )

        invoice_items.append(
            TaskReviewSummaryInvoiceItem(
                invoice=invoice,
                supporting_material_ids=supporting_material_ids_by_invoice_id.get(invoice.id, []),
                validations=validations,
                splits=split_items,
            )
        )

    pending_recognition_count = 0
    failed_recognition_count = 0
    needs_confirmation_recognition_count = 0
    for material_item in material_items:
        recognition = material_item.latest_recognition
        if recognition is None:
            continue
        if recognition.status is RecognitionTaskStatus.PENDING:
            pending_recognition_count += 1
        elif recognition.status is RecognitionTaskStatus.FAILED:
            failed_recognition_count += 1
        elif recognition.status is RecognitionTaskStatus.NEEDS_CONFIRMATION:
            needs_confirmation_recognition_count += 1

    return TaskReviewSummary(
        task_id=task.id,
        administrator_id=normalized_administrator_id,
        counts=TaskReviewSummaryCounts(
            material_count=len(material_items),
            pending_assignment_material_count=len(pending_assignment_materials),
            invoice_count=len(invoice_items),
            validation_count=validation_count,
            blocker_failed_validation_count=blocker_failed_validation_count,
            split_count=split_count,
            confirmed_split_count=confirmed_split_count,
            pending_confirmation_count=pending_confirmation_count,
            disputed_confirmation_count=disputed_confirmation_count,
            missing_confirmation_count=missing_confirmation_count,
            pending_recognition_count=pending_recognition_count,
            failed_recognition_count=failed_recognition_count,
            needs_confirmation_recognition_count=needs_confirmation_recognition_count,
        ),
        materials=material_items,
        pending_assignment_materials=pending_assignment_materials,
        invoices=invoice_items,
    )
