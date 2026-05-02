from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from trms_backend.domain.invoice_validation import (
    AIRFARE_ITINERARY_REQUIRED_RULE_CODE,
    COMPETITION_NOTICE_REQUIRED_RULE_CODE,
    LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
    PAYMENT_RECORD_REQUIRED_RULE_CODE,
)
from trms_backend.domain.invoices import ExpenseType, InvoiceRecord, ValidationResult, ValidationStatus
from trms_backend.domain.materials import MaterialRecord, MaterialType
from trms_backend.domain.tasks import ReimbursementTask, is_task_administrator

_MISSING_MATERIAL_RULE_TO_TYPE = {
    PAYMENT_RECORD_REQUIRED_RULE_CODE: MaterialType.PAYMENT_RECORD,
    COMPETITION_NOTICE_REQUIRED_RULE_CODE: MaterialType.COMPETITION_NOTICE,
    AIRFARE_ITINERARY_REQUIRED_RULE_CODE: MaterialType.ITINERARY,
    # The current domain model has no dedicated "trip information" material type,
    # so rideshare trip evidence is conservatively exported as itinerary-like input.
    LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE: MaterialType.ITINERARY,
}


class MissingMaterialItem(BaseModel):
    task_id: str
    member_id: str | None
    invoice_id: str
    invoice_number: str
    expense_type: ExpenseType
    required_material_type: MaterialType
    source_rule_code: str
    message: str
    evidence: dict[str, Any]
    detected_at: datetime


class MemberMissingMaterialList(BaseModel):
    member_id: str
    items: list[MissingMaterialItem] = Field(default_factory=list)


class TaskMissingMaterialList(BaseModel):
    task_id: str
    items: list[MissingMaterialItem] = Field(default_factory=list)
    members: list[MemberMissingMaterialList] = Field(default_factory=list)


class MissingMaterialViewScope(StrEnum):
    TASK = "task"
    MEMBER = "member"


class VisibleMissingMaterialList(BaseModel):
    task_id: str
    actor_id: str
    scope: MissingMaterialViewScope
    items: list[MissingMaterialItem] = Field(default_factory=list)


class TaskMissingMaterialActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to view missing materials for this task")


def aggregate_task_missing_materials(
    *,
    task_id: str,
    invoices: list[InvoiceRecord],
    materials_by_id: dict[str, MaterialRecord],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
) -> TaskMissingMaterialList:
    items: list[MissingMaterialItem] = []

    for invoice in sorted(invoices, key=lambda item: (item.created_at, item.id)):
        if invoice.task_id != task_id:
            continue

        submitter_id = None
        invoice_material = materials_by_id.get(invoice.material_id)
        if invoice_material is not None:
            submitter_id = invoice_material.submitter_id

        validations = validations_by_invoice_id.get(invoice.id, [])
        for validation in sorted(validations, key=lambda item: (item.created_at, item.id)):
            required_material_type = _resolve_missing_material_type(validation)
            if required_material_type is None:
                continue
            items.append(
                MissingMaterialItem(
                    task_id=task_id,
                    member_id=submitter_id,
                    invoice_id=invoice.id,
                    invoice_number=invoice.invoice_number,
                    expense_type=invoice.expense_type,
                    required_material_type=required_material_type,
                    source_rule_code=validation.rule_code,
                    message=validation.message,
                    evidence=validation.evidence,
                    detected_at=validation.created_at,
                )
            )

    members: list[MemberMissingMaterialList] = []
    items_by_member_id: dict[str, list[MissingMaterialItem]] = {}
    for item in items:
        if item.member_id is None:
            continue
        items_by_member_id.setdefault(item.member_id, []).append(item)
    for member_id, member_items in items_by_member_id.items():
        members.append(MemberMissingMaterialList(member_id=member_id, items=member_items))

    return TaskMissingMaterialList(task_id=task_id, items=items, members=members)


def build_visible_missing_material_list(
    task: ReimbursementTask,
    *,
    actor_id: str,
    invoices: list[InvoiceRecord],
    materials_by_id: dict[str, MaterialRecord],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
) -> VisibleMissingMaterialList:
    normalized_actor_id = actor_id.strip()
    missing_materials = aggregate_task_missing_materials(
        task_id=task.id,
        invoices=invoices,
        materials_by_id=materials_by_id,
        validations_by_invoice_id=validations_by_invoice_id,
    )

    if is_task_administrator(task, actor_id=normalized_actor_id):
        return VisibleMissingMaterialList(
            task_id=task.id,
            actor_id=normalized_actor_id,
            scope=MissingMaterialViewScope.TASK,
            items=missing_materials.items,
        )

    if normalized_actor_id in task.member_ids:
        return VisibleMissingMaterialList(
            task_id=task.id,
            actor_id=normalized_actor_id,
            scope=MissingMaterialViewScope.MEMBER,
            items=[
                item for item in missing_materials.items if item.member_id == normalized_actor_id
            ],
        )

    raise TaskMissingMaterialActorNotAllowedError()


def _resolve_missing_material_type(validation: ValidationResult) -> MaterialType | None:
    if not is_missing_material_validation_result(validation):
        return None
    return _MISSING_MATERIAL_RULE_TO_TYPE.get(validation.rule_code)


def is_missing_material_validation_result(validation: ValidationResult) -> bool:
    return (
        validation.status is ValidationStatus.FAILED
        and validation.rule_code in _MISSING_MATERIAL_RULE_TO_TYPE
    )
