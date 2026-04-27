from datetime import datetime, timezone
from uuid import uuid4

from trms_backend.domain.invoices import (
    InvoiceRecord,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from trms_backend.domain.tasks import ReimbursementTask


def validate_invoice(
    invoice: InvoiceRecord,
    task: ReimbursementTask,
    duplicate_invoice_id: str | None,
) -> list[ValidationResult]:
    return [
        _validation_result(
            rule_code="invoice_title_match",
            target_id=invoice.id,
            status=(
                ValidationStatus.PASSED
                if invoice.buyer_name == task.invoice_title
                else ValidationStatus.FAILED
            ),
            message=(
                "发票抬头匹配"
                if invoice.buyer_name == task.invoice_title
                else f"发票抬头应为 {task.invoice_title}"
            ),
        ),
        _validation_result(
            rule_code="invoice_tax_number_match",
            target_id=invoice.id,
            status=(
                ValidationStatus.PASSED
                if invoice.tax_number == task.tax_number
                else ValidationStatus.FAILED
            ),
            message=(
                "发票税号匹配"
                if invoice.tax_number == task.tax_number
                else "发票税号与任务配置不一致"
            ),
        ),
        _validation_result(
            rule_code="invoice_number_unique",
            target_id=invoice.id,
            status=ValidationStatus.PASSED if duplicate_invoice_id is None else ValidationStatus.FAILED,
            message=(
                "发票号码未重复"
                if duplicate_invoice_id is None
                else f"发票号码与 {duplicate_invoice_id} 重复"
            ),
        ),
    ]


def _validation_result(
    rule_code: str,
    target_id: str,
    status: ValidationStatus,
    message: str,
) -> ValidationResult:
    return ValidationResult(
        id=str(uuid4()),
        rule_code=rule_code,
        target_type="invoice",
        target_id=target_id,
        severity=ValidationSeverity.BLOCKER,
        status=status,
        message=message,
        created_at=datetime.now(timezone.utc),
    )

