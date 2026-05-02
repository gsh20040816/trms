from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from trms_backend.application.supporting_material_auto_link import SupportingMaterialAutoLinkService
from trms_backend.domain.invoices import ExpenseType, InvoiceRecord
from trms_backend.domain.materials import MaterialRecord, MaterialStatus, MaterialType
from trms_backend.domain.tasks import ReimbursementTask


class PendingSupportingMaterialLinkageReason(StrEnum):
    NO_CANDIDATE = "no_candidate"
    MANUAL_CONFIRMATION_REQUIRED = "manual_confirmation_required"
    MULTIPLE_CANDIDATES = "multiple_candidates"


class PendingSupportingMaterialLinkageCandidateInvoiceSummary(BaseModel):
    invoice_id: str
    invoice_number: str
    amount_cents: int = Field(ge=0)
    expense_type: ExpenseType
    original_filename: str


class PendingSupportingMaterialLinkageItem(BaseModel):
    material_id: str
    submitter_id: str
    material_type: MaterialType
    original_filename: str
    pending_reason: PendingSupportingMaterialLinkageReason
    linked_invoices: list[PendingSupportingMaterialLinkageCandidateInvoiceSummary] = Field(
        default_factory=list
    )
    candidate_invoices: list[PendingSupportingMaterialLinkageCandidateInvoiceSummary] = Field(
        default_factory=list
    )
    created_at: datetime


class TaskSupportingMaterialLinkageReport(BaseModel):
    task_id: str
    actor_id: str
    items: list[PendingSupportingMaterialLinkageItem] = Field(default_factory=list)


def build_task_supporting_material_linkage_report(
    task: ReimbursementTask,
    *,
    actor_id: str,
    include_all_members: bool,
    materials: list[MaterialRecord],
    invoices: list[InvoiceRecord],
    materials_by_id: dict[str, MaterialRecord],
    linked_invoice_ids_by_material_id: dict[str, list[str]],
    supporting_material_auto_link_service: SupportingMaterialAutoLinkService,
) -> TaskSupportingMaterialLinkageReport:
    normalized_actor_id = actor_id.strip()
    invoices_by_id = {invoice.id: invoice for invoice in invoices}

    items: list[PendingSupportingMaterialLinkageItem] = []
    for material in sorted(materials, key=lambda item: (item.created_at, item.id)):
        if material.task_id != task.id:
            continue
        if material.status is not MaterialStatus.ASSIGNED:
            continue
        if material.material_type is MaterialType.INVOICE:
            continue
        if material.submitter_id is None:
            continue
        if not include_all_members and material.submitter_id != normalized_actor_id:
            continue
        candidate_invoice_ids = supporting_material_auto_link_service.list_manual_candidate_invoice_ids_for_material(
            material
        )
        candidate_invoices = [
            invoices_by_id[invoice_id]
            for invoice_id in candidate_invoice_ids
            if invoice_id in invoices_by_id
        ]
        linked_invoice_ids = set(linked_invoice_ids_by_material_id.get(material.id, []))

        if len(candidate_invoices) == 0:
            if linked_invoice_ids:
                continue
            pending_reason = PendingSupportingMaterialLinkageReason.NO_CANDIDATE
            linked_invoices: list[InvoiceRecord] = []
            remaining_candidate_invoices: list[InvoiceRecord] = []
        else:
            linked_invoices = [
                invoice for invoice in candidate_invoices if invoice.id in linked_invoice_ids
            ]
            remaining_candidate_invoices = [
                invoice for invoice in candidate_invoices if invoice.id not in linked_invoice_ids
            ]
            if not linked_invoice_ids and len(remaining_candidate_invoices) == 1:
                pending_reason = PendingSupportingMaterialLinkageReason.MANUAL_CONFIRMATION_REQUIRED
            else:
                pending_reason = PendingSupportingMaterialLinkageReason.MULTIPLE_CANDIDATES
            if len(remaining_candidate_invoices) == 0:
                continue

        if (
            pending_reason is PendingSupportingMaterialLinkageReason.NO_CANDIDATE
            and linked_invoices
        ):
            continue

        items.append(
            PendingSupportingMaterialLinkageItem(
                material_id=material.id,
                submitter_id=material.submitter_id,
                material_type=material.material_type,
                original_filename=material.original_filename,
                pending_reason=pending_reason,
                linked_invoices=[
                    build_pending_supporting_material_candidate_invoice_summary(
                        invoice,
                        materials_by_id=materials_by_id,
                    )
                    for invoice in linked_invoices
                ],
                candidate_invoices=[
                    build_pending_supporting_material_candidate_invoice_summary(
                        invoice,
                        materials_by_id=materials_by_id,
                    )
                    for invoice in remaining_candidate_invoices
                ],
                created_at=material.created_at,
            )
        )

    return TaskSupportingMaterialLinkageReport(
        task_id=task.id,
        actor_id=normalized_actor_id,
        items=items,
    )


def build_pending_supporting_material_candidate_invoice_summary(
    invoice: InvoiceRecord,
    *,
    materials_by_id: dict[str, MaterialRecord],
) -> PendingSupportingMaterialLinkageCandidateInvoiceSummary:
    invoice_material = materials_by_id.get(invoice.material_id)
    return PendingSupportingMaterialLinkageCandidateInvoiceSummary(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        amount_cents=invoice.amount_cents,
        expense_type=invoice.expense_type,
        original_filename=(
            invoice_material.original_filename if invoice_material is not None else invoice.invoice_number
        ),
    )
