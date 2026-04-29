from __future__ import annotations

from trms_backend.domain.invoices import (
    InvoiceRecord,
    InvoiceRepository,
    InvoiceSupportingMaterialLinkRecord,
)
from trms_backend.domain.materials import (
    MaterialRecord,
    MaterialRepository,
    MaterialStatus,
    MaterialType,
)


class SupportingMaterialAutoLinkService:
    def __init__(
        self,
        *,
        material_repository: MaterialRepository,
        invoice_repository: InvoiceRepository,
    ) -> None:
        self._material_repository = material_repository
        self._invoice_repository = invoice_repository

    def auto_link_for_invoice(self, invoice: InvoiceRecord) -> list[InvoiceSupportingMaterialLinkRecord]:
        invoice_material = self._material_repository.get(invoice.material_id)
        if invoice_material is None:
            return []
        if not _is_assigned_supporting_link_context(invoice_material):
            return []

        linked: list[InvoiceSupportingMaterialLinkRecord] = []
        for material in self._material_repository.list_by_task(invoice.task_id):
            if material.id == invoice.material_id:
                continue
            if not self._is_auto_linkable_supporting_material(material):
                continue
            if material.submitter_id != invoice_material.submitter_id:
                continue
            candidate_invoice_ids = self._candidate_invoice_ids_for_material(material)
            if candidate_invoice_ids != [invoice.id]:
                continue
            linked.append(
                self._invoice_repository.attach_supporting_material(
                    invoice.id,
                    material.id,
                )
            )
        return linked

    def auto_link_for_material(self, material: MaterialRecord) -> list[InvoiceSupportingMaterialLinkRecord]:
        if not self._is_auto_linkable_supporting_material(material):
            return []

        candidate_invoice_ids = self._candidate_invoice_ids_for_material(material)
        if len(candidate_invoice_ids) != 1:
            return []
        return [
            self._invoice_repository.attach_supporting_material(
                candidate_invoice_ids[0],
                material.id,
            )
        ]

    def _is_auto_linkable_supporting_material(self, material: MaterialRecord) -> bool:
        if not _is_assigned_supporting_link_context(material):
            return False
        if material.material_type is MaterialType.INVOICE:
            return False
        if self._invoice_repository.list_by_supporting_material(material.id):
            return False
        return True

    def _candidate_invoice_ids_for_material(self, material: MaterialRecord) -> list[str]:
        task_id = material.task_id
        submitter_id = material.submitter_id
        if task_id is None or submitter_id is None:
            return []

        candidate_invoice_ids: list[str] = []
        for invoice in self._invoice_repository.list_by_task(task_id):
            invoice_material = self._material_repository.get(invoice.material_id)
            if invoice_material is None:
                continue
            if invoice_material.submitter_id != submitter_id:
                continue
            candidate_invoice_ids.append(invoice.id)
        return candidate_invoice_ids


def _is_assigned_supporting_link_context(material: MaterialRecord) -> bool:
    return (
        material.status is MaterialStatus.ASSIGNED
        and material.task_id is not None
        and material.submitter_id is not None
    )
