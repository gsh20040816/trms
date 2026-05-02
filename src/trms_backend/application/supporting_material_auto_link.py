from __future__ import annotations

from datetime import date

from trms_backend.domain.invoices import ExpenseType
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
from trms_backend.domain.recognitions import RecognitionTaskRecord, RecognitionTaskRepository

LOCAL_TRANSPORT_ITINERARY_AMOUNT_FIELD_NAMES = ("amount_cents",)
LOCAL_TRANSPORT_ITINERARY_TIME_FIELD_NAMES = ("transaction_time",)
LOCAL_TRANSPORT_ITINERARY_EXPENSE_TYPE_FIELD_NAMES = ("expense_type", "expense_type_candidate")

AUTO_LINKABLE_SUPPORTING_MATERIAL_TYPES = frozenset(
    {
        MaterialType.PAYMENT_RECORD,
        MaterialType.COMPETITION_NOTICE,
        MaterialType.ITINERARY,
        MaterialType.ORDER_SCREENSHOT,
    }
)


class SupportingMaterialAutoLinkService:
    def __init__(
        self,
        *,
        material_repository: MaterialRepository,
        invoice_repository: InvoiceRepository,
        recognition_task_repository: RecognitionTaskRepository,
    ) -> None:
        self._material_repository = material_repository
        self._invoice_repository = invoice_repository
        self._recognition_task_repository = recognition_task_repository

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

    def auto_link_for_material(
        self,
        material: MaterialRecord,
        *,
        recognition_task: RecognitionTaskRecord | None = None,
    ) -> list[InvoiceSupportingMaterialLinkRecord]:
        if not self._is_auto_linkable_supporting_material(material):
            return []

        candidate_invoice_ids = self._auto_link_candidate_invoice_ids_for_material(
            material,
            recognition_task=recognition_task,
        )
        if len(candidate_invoice_ids) != 1:
            return []
        return [
            self._invoice_repository.attach_supporting_material(
                candidate_invoice_ids[0],
                material.id,
            )
        ]

    def list_manual_candidate_invoice_ids_for_material(
        self,
        material: MaterialRecord,
        *,
        recognition_task: RecognitionTaskRecord | None = None,
    ) -> list[str]:
        if not _is_assigned_supporting_link_context(material):
            return []
        return self._candidate_invoice_ids_for_material(
            material,
            recognition_task=recognition_task,
        )

    def _is_auto_linkable_supporting_material(self, material: MaterialRecord) -> bool:
        if not _is_assigned_supporting_link_context(material):
            return False
        if material.material_type not in AUTO_LINKABLE_SUPPORTING_MATERIAL_TYPES:
            return False
        if self._invoice_repository.list_by_supporting_material(material.id):
            return False
        return True

    def _candidate_invoice_ids_for_material(
        self,
        material: MaterialRecord,
        *,
        recognition_task: RecognitionTaskRecord | None = None,
    ) -> list[str]:
        task_id = material.task_id
        submitter_id = material.submitter_id
        if task_id is None or submitter_id is None:
            return []

        candidate_invoices: list[InvoiceRecord] = []
        for invoice in self._invoice_repository.list_by_task(task_id):
            invoice_material = self._material_repository.get(invoice.material_id)
            if invoice_material is None:
                continue
            if invoice_material.submitter_id != submitter_id:
                continue
            candidate_invoices.append(invoice)
        return self._prioritize_candidate_invoices(
            material,
            candidate_invoices,
            recognition_task=recognition_task,
        )

    def _auto_link_candidate_invoice_ids_for_material(
        self,
        material: MaterialRecord,
        *,
        recognition_task: RecognitionTaskRecord | None = None,
    ) -> list[str]:
        candidate_invoice_ids = self._candidate_invoice_ids_for_material(
            material,
            recognition_task=recognition_task,
        )
        if len(candidate_invoice_ids) != 1:
            return []

        effective_recognition_task = recognition_task
        if effective_recognition_task is None:
            effective_recognition_task = self._recognition_task_repository.get_latest_effective_by_material(
                material.id
            )
        recognized_amount_cents = _extract_first_int_field(
            effective_recognition_task,
            LOCAL_TRANSPORT_ITINERARY_AMOUNT_FIELD_NAMES,
        )
        if recognized_amount_cents is None:
            return []

        candidate_invoice = self._invoice_repository.get(candidate_invoice_ids[0])
        if candidate_invoice is None:
            return []
        if candidate_invoice.amount_cents != recognized_amount_cents:
            return []
        return candidate_invoice_ids

    def _prioritize_candidate_invoices(
        self,
        material: MaterialRecord,
        candidate_invoices: list[InvoiceRecord],
        *,
        recognition_task: RecognitionTaskRecord | None = None,
    ) -> list[str]:
        effective_recognition_task = recognition_task
        if effective_recognition_task is None:
            effective_recognition_task = self._recognition_task_repository.get_latest_effective_by_material(
                material.id
            )

        if material.material_type is not MaterialType.ITINERARY:
            return _prioritize_by_exact_amount_match(
                candidate_invoices,
                recognized_amount_cents=_extract_first_int_field(
                    effective_recognition_task,
                    LOCAL_TRANSPORT_ITINERARY_AMOUNT_FIELD_NAMES,
                ),
            )

        itinerary_recognition = effective_recognition_task
        if itinerary_recognition is None:
            return []
        if not _is_local_transport_itinerary(itinerary_recognition):
            return _prioritize_by_exact_amount_match(
                candidate_invoices,
                recognized_amount_cents=_extract_first_int_field(
                    itinerary_recognition,
                    LOCAL_TRANSPORT_ITINERARY_AMOUNT_FIELD_NAMES,
                ),
            )

        local_transport_candidates = [
            invoice
            for invoice in candidate_invoices
            if invoice.expense_type is ExpenseType.LOCAL_TRANSPORT
        ]
        if not local_transport_candidates:
            return []

        itinerary_amount_cents = _extract_first_int_field(
            itinerary_recognition,
            LOCAL_TRANSPORT_ITINERARY_AMOUNT_FIELD_NAMES,
        )
        itinerary_transaction_date = _extract_first_date_field(
            itinerary_recognition,
            LOCAL_TRANSPORT_ITINERARY_TIME_FIELD_NAMES,
        )
        scored_candidates: list[tuple[InvoiceRecord, int]] = []
        for invoice in local_transport_candidates:
            score = 100
            if itinerary_amount_cents is not None and invoice.amount_cents == itinerary_amount_cents:
                score += 50
            if (
                itinerary_transaction_date is not None
                and invoice.transaction_time is not None
                and invoice.transaction_time.date() == itinerary_transaction_date
            ):
                score += 30
            scored_candidates.append((invoice, score))

        best_score = max(score for _, score in scored_candidates)
        if best_score <= 100:
            return []
        best_candidates = [
            invoice.id for invoice, score in scored_candidates if score == best_score
        ]
        if len(best_candidates) == 1:
            return best_candidates
        return best_candidates


def _prioritize_by_exact_amount_match(
    candidate_invoices: list[InvoiceRecord],
    *,
    recognized_amount_cents: int | None,
) -> list[str]:
    if recognized_amount_cents is None:
        return [invoice.id for invoice in candidate_invoices]

    exact_match_ids = [
        invoice.id
        for invoice in candidate_invoices
        if invoice.amount_cents == recognized_amount_cents
    ]
    other_ids = [
        invoice.id
        for invoice in candidate_invoices
        if invoice.amount_cents != recognized_amount_cents
    ]
    return [*exact_match_ids, *other_ids]


def _is_assigned_supporting_link_context(material: MaterialRecord) -> bool:
    return (
        material.status is MaterialStatus.ASSIGNED
        and material.task_id is not None
        and material.submitter_id is not None
    )


def _is_local_transport_itinerary(recognition_task: RecognitionTaskRecord | None) -> bool:
    if recognition_task is None:
        return False
    for field_name in LOCAL_TRANSPORT_ITINERARY_EXPENSE_TYPE_FIELD_NAMES:
        field_result = recognition_task.recognized_fields.get(field_name)
        if field_result is None:
            continue
        if field_result.value == ExpenseType.LOCAL_TRANSPORT.value:
            return True
    return False


def _extract_first_int_field(
    recognition_task: RecognitionTaskRecord | None,
    field_names: tuple[str, ...],
) -> int | None:
    if recognition_task is None:
        return None
    for field_name in field_names:
        field_result = recognition_task.recognized_fields.get(field_name)
        if field_result is None or not isinstance(field_result.value, int):
            continue
        return field_result.value
    return None


def _extract_first_date_field(
    recognition_task: RecognitionTaskRecord | None,
    field_names: tuple[str, ...],
) -> date | None:
    if recognition_task is None:
        return None
    for field_name in field_names:
        field_result = recognition_task.recognized_fields.get(field_name)
        if field_result is None:
            continue
        field_value = field_result.value
        if hasattr(field_value, "date"):
            field_date = field_value.date()
            if isinstance(field_date, date):
                return field_date
    return None
