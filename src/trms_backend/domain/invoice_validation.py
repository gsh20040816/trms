from datetime import datetime, timezone
from uuid import uuid4

from trms_backend.domain.invoices import (
    InvoiceRecord,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from trms_backend.domain.materials import MaterialRecord, MaterialType
from trms_backend.domain.recognitions import RecognitionTaskRecord
from trms_backend.domain.tasks import ReimbursementTask

PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS = 100_000
PAYMENT_RECORD_REQUIRED_RULE_CODE = "invoice_payment_record_required"


def validate_invoice(
    invoice: InvoiceRecord,
    task: ReimbursementTask,
    duplicate_invoice_id: str | None,
    recognition_task: RecognitionTaskRecord | None = None,
    supporting_materials: list[MaterialRecord] | None = None,
) -> list[ValidationResult]:
    invoice_number_is_unique = duplicate_invoice_id is None
    supporting_materials = supporting_materials or []
    return [
        _validate_invoice_title(invoice, task, recognition_task),
        _validate_invoice_tax_number(invoice, task, recognition_task),
        _validation_result(
            rule_code="invoice_number_unique",
            target_id=invoice.id,
            status=ValidationStatus.PASSED if invoice_number_is_unique else ValidationStatus.FAILED,
            message=(
                "发票号码未重复"
                if invoice_number_is_unique
                else f"发票号码与 {duplicate_invoice_id} 重复"
            ),
            evidence={
                "invoice_number": invoice.invoice_number,
                "duplicate_invoice_id": duplicate_invoice_id,
            },
        ),
        validate_payment_record_requirement(invoice, supporting_materials),
    ]


def _validate_invoice_title(
    invoice: InvoiceRecord,
    task: ReimbursementTask,
    recognition_task: RecognitionTaskRecord | None,
) -> ValidationResult:
    title_matches = invoice.buyer_name == task.invoice_title
    if recognition_task is not None:
        recognized_buyer_name_field = recognition_task.recognized_fields.get("buyer_name")
        if recognized_buyer_name_field is None:
            return _validation_result(
                rule_code="invoice_title_match",
                target_id=invoice.id,
                status=ValidationStatus.PENDING if title_matches else ValidationStatus.FAILED,
                message=(
                    "发票抬头未识别，需人工确认"
                    if title_matches
                    else f"发票抬头未识别，且人工录入值应为 {task.invoice_title}"
                ),
                evidence={
                    "expected_buyer_name": task.invoice_title,
                    "actual_buyer_name": invoice.buyer_name,
                    "recognized_buyer_name": None,
                    "recognition_task_status": recognition_task.status.value,
                    "recognition_status": "missing",
                },
            )
    return _validation_result(
        rule_code="invoice_title_match",
        target_id=invoice.id,
        status=ValidationStatus.PASSED if title_matches else ValidationStatus.FAILED,
        message=(
            "发票抬头匹配"
            if title_matches
            else f"发票抬头应为 {task.invoice_title}"
        ),
        evidence={
            "expected_buyer_name": task.invoice_title,
            "actual_buyer_name": invoice.buyer_name,
        },
    )


def _validate_invoice_tax_number(
    invoice: InvoiceRecord,
    task: ReimbursementTask,
    recognition_task: RecognitionTaskRecord | None,
) -> ValidationResult:
    tax_number_matches = invoice.tax_number == task.tax_number
    if recognition_task is not None:
        recognized_tax_number_field = recognition_task.recognized_fields.get("tax_number")
        if recognized_tax_number_field is None:
            return _validation_result(
                rule_code="invoice_tax_number_match",
                target_id=invoice.id,
                status=ValidationStatus.PENDING if tax_number_matches else ValidationStatus.FAILED,
                message=(
                    "发票税号未识别，需人工确认"
                    if tax_number_matches
                    else "发票税号未识别，且人工录入值与任务配置不一致"
                ),
                evidence={
                    "expected_tax_number": task.tax_number,
                    "actual_tax_number": invoice.tax_number,
                    "recognized_tax_number": None,
                    "recognition_task_status": recognition_task.status.value,
                    "recognition_status": "missing",
                },
            )
    return _validation_result(
        rule_code="invoice_tax_number_match",
        target_id=invoice.id,
        status=ValidationStatus.PASSED if tax_number_matches else ValidationStatus.FAILED,
        message=(
            "发票税号匹配"
            if tax_number_matches
            else "发票税号与任务配置不一致"
        ),
        evidence={
            "expected_tax_number": task.tax_number,
            "actual_tax_number": invoice.tax_number,
        },
    )


def _validation_result(
    rule_code: str,
    target_id: str,
    status: ValidationStatus,
    message: str,
    evidence: dict[str, object | None],
) -> ValidationResult:
    return ValidationResult(
        id=str(uuid4()),
        rule_code=rule_code,
        target_type="invoice",
        target_id=target_id,
        severity=ValidationSeverity.BLOCKER,
        status=status,
        message=message,
        evidence=evidence,
        created_at=datetime.now(timezone.utc),
    )


def validate_payment_record_requirement(
    invoice: InvoiceRecord,
    supporting_materials: list[MaterialRecord],
) -> ValidationResult:
    threshold_cents = PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS
    payment_record_material_ids = [
        material.id
        for material in supporting_materials
        if material.material_type is MaterialType.PAYMENT_RECORD
    ]
    requires_payment_record = invoice.amount_cents >= threshold_cents
    has_payment_record = len(payment_record_material_ids) > 0

    if not requires_payment_record:
        return _validation_result(
            rule_code=PAYMENT_RECORD_REQUIRED_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="发票金额未达到支付记录必需阈值",
            evidence={
                "amount_cents": invoice.amount_cents,
                "threshold_amount_cents": threshold_cents,
                "config_source": (
                    "trms_backend.domain.invoice_validation."
                    "PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS"
                ),
                "requires_payment_record": False,
                "payment_record_material_ids": payment_record_material_ids,
            },
        )

    if has_payment_record:
        return _validation_result(
            rule_code=PAYMENT_RECORD_REQUIRED_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message="发票金额达到阈值，已关联支付记录",
            evidence={
                "amount_cents": invoice.amount_cents,
                "threshold_amount_cents": threshold_cents,
                "config_source": (
                    "trms_backend.domain.invoice_validation."
                    "PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS"
                ),
                "requires_payment_record": True,
                "payment_record_material_ids": payment_record_material_ids,
            },
        )

    return _validation_result(
        rule_code=PAYMENT_RECORD_REQUIRED_RULE_CODE,
        target_id=invoice.id,
        status=ValidationStatus.FAILED,
        message="发票金额达到阈值，缺少支付记录",
        evidence={
            "amount_cents": invoice.amount_cents,
            "threshold_amount_cents": threshold_cents,
            "config_source": (
                "trms_backend.domain.invoice_validation."
                "PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS"
            ),
            "requires_payment_record": True,
            "payment_record_material_ids": payment_record_material_ids,
        },
    )
