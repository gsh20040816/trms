from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.expense_details import ExpenseDetailItem, build_expense_detail_list
from trms_backend.domain.invoices import InvoiceRecord, ValidationResult, ValidationStatus
from trms_backend.domain.materials import MaterialRecord, MaterialStatus, MaterialType
from trms_backend.domain.missing_materials import MissingMaterialItem, build_visible_missing_material_list
from trms_backend.domain.recognitions import RecognitionTaskRecord, RecognitionTaskStatus
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.tasks import ReimbursementTask


MEMBER_SUBMISSION_IGNORED_RULE_CODES = {"invoice_paper_receipt_required"}


class TaskMemberStatusActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to view member status for this task")


class TaskMemberMaterialStatusItem(BaseModel):
    material_id: str
    submitter_id: str
    material_type: MaterialType
    original_filename: str
    material_status: MaterialStatus
    recognition_status: RecognitionTaskStatus | None = None
    recognition_failure_stage: str | None = None
    recognition_failure_reason: str | None = None
    invoice_id: str | None = None
    invoice_number: str | None = None
    validation_status: ValidationStatus
    validation_messages: list[str] = Field(default_factory=list)
    created_at: datetime


class TaskMemberStatusCounts(BaseModel):
    material_count: int = Field(ge=0)
    missing_material_count: int = Field(ge=0)
    expense_detail_count: int = Field(ge=0)
    recognition_pending_count: int = Field(ge=0)
    recognition_succeeded_count: int = Field(ge=0)
    recognition_failed_count: int = Field(ge=0)
    recognition_needs_confirmation_count: int = Field(ge=0)
    validation_passed_count: int = Field(ge=0)
    validation_failed_count: int = Field(ge=0)
    validation_pending_count: int = Field(ge=0)
    validation_not_applicable_count: int = Field(ge=0)
    confirmed_expense_count: int = Field(ge=0)
    pending_confirmation_count: int = Field(ge=0)
    disputed_confirmation_count: int = Field(ge=0)
    missing_confirmation_count: int = Field(ge=0)


class TaskMemberStatusReport(BaseModel):
    task_id: str
    actor_id: str
    total_expense_amount_cents: int = Field(ge=0)
    counts: TaskMemberStatusCounts
    materials: list[TaskMemberMaterialStatusItem] = Field(default_factory=list)
    missing_materials: list[MissingMaterialItem] = Field(default_factory=list)
    expense_details: list[ExpenseDetailItem] = Field(default_factory=list)


def build_task_member_status_report(
    task: ReimbursementTask,
    *,
    actor_id: str,
    materials: list[MaterialRecord],
    invoices: list[InvoiceRecord],
    latest_recognitions_by_material_id: dict[str, RecognitionTaskRecord | None],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
) -> TaskMemberStatusReport:
    normalized_actor_id = actor_id.strip()
    if normalized_actor_id not in task.member_ids:
        raise TaskMemberStatusActorNotAllowedError()

    visible_materials = sorted(
        [
            material
            for material in materials
            if material.task_id == task.id and material.submitter_id == normalized_actor_id
        ],
        key=lambda item: (item.created_at, item.id),
    )
    invoice_by_material_id = {invoice.material_id: invoice for invoice in invoices}

    material_status_items: list[TaskMemberMaterialStatusItem] = []
    for material in visible_materials:
        recognition = latest_recognitions_by_material_id.get(material.id)
        invoice = invoice_by_material_id.get(material.id)
        validations = validations_by_invoice_id.get(invoice.id, []) if invoice is not None else []
        material_status_items.append(
            TaskMemberMaterialStatusItem(
                material_id=material.id,
                submitter_id=normalized_actor_id,
                material_type=material.material_type,
                original_filename=material.original_filename,
                material_status=material.status,
                recognition_status=(recognition.status if recognition is not None else None),
                recognition_failure_stage=(
                    recognition.failure.stage.value
                    if recognition is not None and recognition.failure is not None
                    else None
                ),
                recognition_failure_reason=(
                    recognition.failure.reason
                    if recognition is not None and recognition.failure is not None
                    else None
                ),
                invoice_id=invoice.id if invoice is not None else None,
                invoice_number=invoice.invoice_number if invoice is not None else None,
                validation_status=_summarize_validation_status_for_member_submission(validations),
                validation_messages=[
                    validation.message
                    for validation in validations
                    if validation.status in {ValidationStatus.FAILED, ValidationStatus.PENDING}
                    and validation.rule_code not in MEMBER_SUBMISSION_IGNORED_RULE_CODES
                ],
                created_at=material.created_at,
            )
        )

    missing_materials = build_visible_missing_material_list(
        task,
        actor_id=normalized_actor_id,
        invoices=invoices,
        materials_by_id={material.id: material for material in materials},
        validations_by_invoice_id=validations_by_invoice_id,
    ).items
    expense_details = build_expense_detail_list(
        task,
        actor_id=normalized_actor_id,
        invoices=invoices,
        splits_by_invoice_id=splits_by_invoice_id,
        confirmations_by_split_id=confirmations_by_split_id,
    )

    recognition_counts = {
        RecognitionTaskStatus.PENDING: 0,
        RecognitionTaskStatus.SUCCEEDED: 0,
        RecognitionTaskStatus.FAILED: 0,
        RecognitionTaskStatus.NEEDS_CONFIRMATION: 0,
    }
    validation_counts = {
        ValidationStatus.PASSED: 0,
        ValidationStatus.FAILED: 0,
        ValidationStatus.PENDING: 0,
        ValidationStatus.NOT_APPLICABLE: 0,
    }
    for item in material_status_items:
        if item.recognition_status is not None:
            recognition_counts[item.recognition_status] += 1
        validation_counts[item.validation_status] += 1

    confirmed_expense_count = 0
    pending_confirmation_count = 0
    disputed_confirmation_count = 0
    missing_confirmation_count = 0
    for item in expense_details.items:
        if item.confirmation is None:
            missing_confirmation_count += 1
            continue
        if item.confirmation.status is ConfirmationStatus.CONFIRMED:
            confirmed_expense_count += 1
        elif item.confirmation.status is ConfirmationStatus.PENDING:
            pending_confirmation_count += 1
        else:
            disputed_confirmation_count += 1

    return TaskMemberStatusReport(
        task_id=task.id,
        actor_id=normalized_actor_id,
        total_expense_amount_cents=expense_details.total_amount_cents,
        counts=TaskMemberStatusCounts(
            material_count=len(material_status_items),
            missing_material_count=len(missing_materials),
            expense_detail_count=len(expense_details.items),
            recognition_pending_count=recognition_counts[RecognitionTaskStatus.PENDING],
            recognition_succeeded_count=recognition_counts[RecognitionTaskStatus.SUCCEEDED],
            recognition_failed_count=recognition_counts[RecognitionTaskStatus.FAILED],
            recognition_needs_confirmation_count=(
                recognition_counts[RecognitionTaskStatus.NEEDS_CONFIRMATION]
            ),
            validation_passed_count=validation_counts[ValidationStatus.PASSED],
            validation_failed_count=validation_counts[ValidationStatus.FAILED],
            validation_pending_count=validation_counts[ValidationStatus.PENDING],
            validation_not_applicable_count=validation_counts[ValidationStatus.NOT_APPLICABLE],
            confirmed_expense_count=confirmed_expense_count,
            pending_confirmation_count=pending_confirmation_count,
            disputed_confirmation_count=disputed_confirmation_count,
            missing_confirmation_count=missing_confirmation_count,
        ),
        materials=material_status_items,
        missing_materials=missing_materials,
        expense_details=expense_details.items,
    )


def _summarize_validation_status(validations: list[ValidationResult]) -> ValidationStatus:
    statuses = {validation.status for validation in validations}
    if ValidationStatus.FAILED in statuses:
        return ValidationStatus.FAILED
    if ValidationStatus.PENDING in statuses:
        return ValidationStatus.PENDING
    if ValidationStatus.PASSED in statuses:
        return ValidationStatus.PASSED
    return ValidationStatus.NOT_APPLICABLE


def _summarize_validation_status_for_member_submission(
    validations: list[ValidationResult],
) -> ValidationStatus:
    filtered_validations = [
        validation
        for validation in validations
        if validation.rule_code not in MEMBER_SUBMISSION_IGNORED_RULE_CODES
    ]
    return _summarize_validation_status(filtered_validations)
