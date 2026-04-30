from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import ValidationError

from trms_backend.application.supporting_material_auto_link import (
    SupportingMaterialAutoLinkService,
)
from trms_backend.domain.invoices import ExpenseType, InvoiceCreate, InvoiceRepository
from trms_backend.domain.materials import MaterialRepository, MaterialStatus, MaterialType
from trms_backend.domain.recognitions import (
    RecognitionFieldResult,
    RecognitionFieldStatus,
    RecognitionTaskRecord,
    RecognitionTaskStatus,
)
from trms_backend.domain.tasks import (
    TaskExpenseTypeNotAllowedError,
    TaskRepository,
    ensure_task_allows_expense_type,
)

_REQUIRED_INVOICE_FIELD_NAMES = frozenset(
    {
        "invoice_number",
        "buyer_name",
        "tax_number",
        "amount_cents",
        "expense_type",
    }
)


class RecognitionInvoiceAutoCreateService:
    def __init__(
        self,
        *,
        task_repository: TaskRepository,
        material_repository: MaterialRepository,
        invoice_repository: InvoiceRepository,
        supporting_material_auto_link_service: SupportingMaterialAutoLinkService,
    ) -> None:
        self._task_repository = task_repository
        self._material_repository = material_repository
        self._invoice_repository = invoice_repository
        self._supporting_material_auto_link_service = supporting_material_auto_link_service

    def try_upsert_invoice_from_recognition(
        self,
        recognition_task: RecognitionTaskRecord,
    ) -> bool:
        if recognition_task.status is not RecognitionTaskStatus.SUCCEEDED:
            return False

        invoice_data = _build_invoice_create_from_recognition(recognition_task.recognized_fields)
        if invoice_data is None:
            return False

        material = self._material_repository.get(recognition_task.material_id)
        if (
            material is None
            or material.status is not MaterialStatus.ASSIGNED
            or material.task_id is None
            or material.material_type is not MaterialType.INVOICE
        ):
            return False

        task = self._task_repository.get(material.task_id)
        if task is None:
            return False

        try:
            ensure_task_allows_expense_type(task, invoice_data.expense_type)
        except TaskExpenseTypeNotAllowedError:
            return False

        invoice = self._invoice_repository.upsert_for_material(
            material.task_id,
            material.id,
            invoice_data,
        )
        self._supporting_material_auto_link_service.auto_link_for_invoice(invoice)
        return True


def _build_invoice_create_from_recognition(
    recognized_fields: dict[str, RecognitionFieldResult],
) -> InvoiceCreate | None:
    if not _REQUIRED_INVOICE_FIELD_NAMES.issubset(recognized_fields):
        return None

    values: dict[str, Any] = {}
    for field_name in (
        "invoice_number",
        "issue_date",
        "transaction_time",
        "buyer_name",
        "tax_number",
        "seller_name",
        "amount_cents",
        "expense_type",
    ):
        field = recognized_fields.get(field_name)
        if field is None:
            continue
        if field.status is not RecognitionFieldStatus.RECOGNIZED:
            return None
        values[field_name] = field.value

    expense_type = values.get("expense_type")
    if not isinstance(expense_type, str):
        return None
    try:
        values["expense_type"] = ExpenseType(expense_type)
    except ValueError:
        return None

    amount_cents = values.get("amount_cents")
    if isinstance(amount_cents, float) and amount_cents.is_integer():
        values["amount_cents"] = int(amount_cents)

    for string_field_name in ("invoice_number", "buyer_name", "tax_number", "seller_name"):
        field_value = values.get(string_field_name)
        if field_value is None:
            continue
        if not isinstance(field_value, str):
            return None
        values[string_field_name] = field_value.strip()

    if "issue_date" in values and isinstance(values["issue_date"], datetime):
        values["issue_date"] = values["issue_date"].date()
    if "issue_date" in values and values["issue_date"] == "":
        values["issue_date"] = None
    if "transaction_time" in values and values["transaction_time"] == "":
        values["transaction_time"] = None

    if isinstance(values.get("issue_date"), str):
        try:
            values["issue_date"] = date.fromisoformat(values["issue_date"])
        except ValueError:
            return None

    try:
        return InvoiceCreate.model_validate(values)
    except ValidationError:
        return None
