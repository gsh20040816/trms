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
PAYMENT_RECORD_AMOUNT_MATCH_MODE = "exact_sum"
PAYMENT_RECORD_AMOUNT_MATCH_RULE_CODE = "invoice_payment_record_amount_match"


def validate_invoice(
    invoice: InvoiceRecord,
    task: ReimbursementTask,
    duplicate_invoice_id: str | None,
    recognition_task: RecognitionTaskRecord | None = None,
    supporting_materials: list[MaterialRecord] | None = None,
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None] | None = None,
) -> list[ValidationResult]:
    invoice_number_is_unique = duplicate_invoice_id is None
    supporting_materials = supporting_materials or []
    supporting_material_recognitions = supporting_material_recognitions or {}
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
        validate_payment_record_amount_match(
            invoice,
            supporting_materials,
            supporting_material_recognitions,
        ),
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


def validate_payment_record_amount_match(
    invoice: InvoiceRecord,
    supporting_materials: list[MaterialRecord],
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None],
) -> ValidationResult:
    threshold_cents = PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS
    payment_record_materials = [
        material
        for material in supporting_materials
        if material.material_type is MaterialType.PAYMENT_RECORD
    ]
    payment_record_material_ids = [material.id for material in payment_record_materials]
    requires_payment_record = invoice.amount_cents >= threshold_cents
    evidence = {
        "invoice_amount_cents": invoice.amount_cents,
        "threshold_amount_cents": threshold_cents,
        "matching_mode": PAYMENT_RECORD_AMOUNT_MATCH_MODE,
        "config_source": (
            "trms_backend.domain.invoice_validation.PAYMENT_RECORD_AMOUNT_MATCH_MODE"
        ),
        "requires_payment_record": requires_payment_record,
        "payment_record_material_ids": payment_record_material_ids,
        "matched_payment_records": [],
        "missing_amount_materials": [],
        "payment_record_amount_total_cents": None,
    }

    if not requires_payment_record:
        return _validation_result(
            rule_code=PAYMENT_RECORD_AMOUNT_MATCH_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="发票金额未达到支付记录金额匹配阈值",
            evidence=evidence,
        )

    if not payment_record_material_ids:
        return _validation_result(
            rule_code=PAYMENT_RECORD_AMOUNT_MATCH_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="尚未关联支付记录，暂不执行金额匹配",
            evidence=evidence,
        )

    matched_payment_records: list[dict[str, object | None]] = []
    missing_amount_materials: list[dict[str, object | None]] = []
    total_amount_cents = 0
    for material in payment_record_materials:
        recognition_task = supporting_material_recognitions.get(material.id)
        recognized_amount_cents = _extract_recognized_amount_cents(recognition_task)
        if recognized_amount_cents is None:
            missing_amount_materials.append(
                {
                    "material_id": material.id,
                    "recognition_task_id": (
                        recognition_task.id if recognition_task is not None else None
                    ),
                    "recognition_task_status": (
                        recognition_task.status.value if recognition_task is not None else None
                    ),
                }
            )
            continue
        matched_payment_records.append(
            {
                "material_id": material.id,
                "recognized_amount_cents": recognized_amount_cents,
                "recognition_task_id": recognition_task.id if recognition_task is not None else None,
                "recognition_task_status": (
                    recognition_task.status.value if recognition_task is not None else None
                ),
            }
        )
        total_amount_cents += recognized_amount_cents

    evidence["matched_payment_records"] = matched_payment_records
    evidence["missing_amount_materials"] = missing_amount_materials
    evidence["payment_record_amount_total_cents"] = total_amount_cents

    if missing_amount_materials:
        return _validation_result(
            rule_code=PAYMENT_RECORD_AMOUNT_MATCH_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PENDING,
            message="支付记录金额缺失，需人工确认",
            evidence=evidence,
        )

    if total_amount_cents == invoice.amount_cents:
        return _validation_result(
            rule_code=PAYMENT_RECORD_AMOUNT_MATCH_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message="支付记录金额与发票金额一致",
            evidence=evidence,
        )

    return _validation_result(
        rule_code=PAYMENT_RECORD_AMOUNT_MATCH_RULE_CODE,
        target_id=invoice.id,
        status=ValidationStatus.FAILED,
        message="支付记录金额合计与发票金额不一致",
        evidence=evidence,
    )


def _extract_recognized_amount_cents(
    recognition_task: RecognitionTaskRecord | None,
) -> int | None:
    if recognition_task is None:
        return None
    amount_field = recognition_task.recognized_fields.get("amount_cents")
    if amount_field is None:
        return None
    return _coerce_amount_cents(amount_field.value)


def _coerce_amount_cents(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        if value.is_integer() and value > 0:
            return int(value)
        return None
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.isdigit():
            parsed = int(normalized)
            return parsed if parsed > 0 else None
    return None
