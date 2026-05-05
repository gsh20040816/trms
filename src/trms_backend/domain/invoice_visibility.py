from __future__ import annotations

from trms_backend.domain.invoices import InvoiceMemberSubmissionStatus, InvoiceRecord
from trms_backend.domain.materials import MaterialRecord
from trms_backend.domain.tasks import ReimbursementTask, is_task_administrator


def is_submitted_invoice(invoice: InvoiceRecord) -> bool:
    return invoice.member_submission_status is InvoiceMemberSubmissionStatus.SUBMITTED


def filter_invoices_visible_to_actor(
    task: ReimbursementTask,
    *,
    actor_id: str,
    invoices: list[InvoiceRecord],
    materials_by_id: dict[str, MaterialRecord],
) -> list[InvoiceRecord]:
    normalized_actor_id = actor_id.strip()
    if is_task_administrator(task, actor_id=normalized_actor_id):
        return [invoice for invoice in invoices if is_submitted_invoice(invoice)]

    if normalized_actor_id not in task.member_ids:
        return []

    visible_invoices: list[InvoiceRecord] = []
    for invoice in invoices:
        material = materials_by_id.get(invoice.material_id)
        if material is not None and material.submitter_id == normalized_actor_id:
            visible_invoices.append(invoice)
            continue
        if is_submitted_invoice(invoice):
            visible_invoices.append(invoice)
    return visible_invoices


def filter_submitted_invoices(invoices: list[InvoiceRecord]) -> list[InvoiceRecord]:
    return [invoice for invoice in invoices if is_submitted_invoice(invoice)]
