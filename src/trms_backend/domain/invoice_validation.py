from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from trms_backend.domain.invoices import (
    ExpenseType,
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
PAPER_INVOICE_RECEIPT_REQUIRED_RULE_CODE = "invoice_paper_receipt_required"
COMPETITION_NOTICE_REQUIRED_RULE_CODE = "invoice_competition_notice_required"
AIRFARE_ITINERARY_REQUIRED_RULE_CODE = "invoice_airfare_itinerary_required"
AIRFARE_CABIN_PROOF_RULE_CODE = "invoice_airfare_cabin_proof_required"
AIRFARE_CABIN_FIELD_NAMES = ("cabin_class", "seat_class", "cabin")
AIRFARE_AIRPORT_CODE_FIELD_GROUPS = (
    ("departure_airport_code", "arrival_airport_code"),
    (
        "departure_airport_code",
        "arrival_airport_code",
        "return_departure_airport_code",
        "return_arrival_airport_code",
    ),
)
LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE = "invoice_local_transport_rideshare_trip_required"
COMPETITION_TIME_RANGE_RULE_CODE = "invoice_competition_time_range"
COMPETITION_LOCATION_RANGE_RULE_CODE = "invoice_competition_location_range"
COMPETITION_TIME_BUFFER_DAYS_BEFORE = 1
COMPETITION_TIME_BUFFER_DAYS_AFTER = 1
COMPETITION_TIME_SUPPORTED_EXPENSE_TYPES = (
    ExpenseType.RAILWAY,
    ExpenseType.AIRFARE,
    ExpenseType.LOCAL_TRANSPORT,
    ExpenseType.HOTEL,
)
COMPETITION_LOCATION_SUPPORTED_EXPENSE_TYPES = COMPETITION_TIME_SUPPORTED_EXPENSE_TYPES
COMPETITION_LOCATION_FIELD_GROUPS = (
    ("transaction_location",),
    ("transaction_city",),
    ("location",),
    ("city",),
    ("merchant_location",),
    ("hotel_city",),
    ("trip_route",),
    ("trip_itinerary",),
    ("departure_location", "arrival_location"),
    ("departure_city", "arrival_city"),
    ("origin_location", "destination_location"),
    ("from_location", "to_location"),
    ("trip_start_location", "trip_end_location"),
    ("pickup_location", "dropoff_location"),
    ("start_location", "end_location"),
)
RIDESHARE_INDICATOR_FIELD_NAMES = (
    "is_rideshare",
    "transport_mode",
    "transport_type",
    "ride_service_type",
)
RIDESHARE_TRUE_VALUES = frozenset({"rideshare", "ride_hailing", "online_taxi", "网约车"})
RIDESHARE_FALSE_VALUES = frozenset({"taxi", "bus", "metro", "subway", "railway", "非网约车"})
RIDESHARE_TRIP_FIELD_GROUPS = (
    ("trip_route",),
    ("trip_itinerary",),
    ("trip_start_location", "trip_end_location"),
    ("pickup_location", "dropoff_location"),
    ("start_location", "end_location"),
)


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
        validate_paper_invoice_receipt_requirement(invoice),
        validate_payment_record_requirement(invoice, supporting_materials),
        validate_payment_record_amount_match(
            invoice,
            supporting_materials,
            supporting_material_recognitions,
        ),
        validate_competition_notice_requirement(invoice, supporting_materials),
        validate_airfare_itinerary_requirement(
            invoice,
            supporting_materials,
            recognition_task,
            supporting_material_recognitions,
        ),
        validate_airfare_cabin_requirement(
            invoice,
            recognition_task,
            supporting_materials,
            supporting_material_recognitions,
        ),
        validate_local_transport_rideshare_trip_requirement(
            invoice,
            recognition_task,
            supporting_materials,
            supporting_material_recognitions,
        ),
        validate_competition_time_range(invoice, task),
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
    severity: ValidationSeverity = ValidationSeverity.BLOCKER,
) -> ValidationResult:
    return ValidationResult(
        id=str(uuid4()),
        rule_code=rule_code,
        target_type="invoice",
        target_id=target_id,
        severity=severity,
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
    has_corporate_transfer_reference = bool(invoice.corporate_transfer_reference)
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
                "corporate_transfer_reference": invoice.corporate_transfer_reference,
                "payment_evidence_mode": "not_required",
            },
        )

    if has_payment_record or has_corporate_transfer_reference:
        return _validation_result(
            rule_code=PAYMENT_RECORD_REQUIRED_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message=(
                "发票金额达到阈值，已填写公对公转账编号"
                if has_corporate_transfer_reference and not has_payment_record
                else "发票金额达到阈值，已关联支付记录"
            ),
            evidence={
                "amount_cents": invoice.amount_cents,
                "threshold_amount_cents": threshold_cents,
                "config_source": (
                    "trms_backend.domain.invoice_validation."
                    "PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS"
                ),
                "requires_payment_record": True,
                "payment_record_material_ids": payment_record_material_ids,
                "corporate_transfer_reference": invoice.corporate_transfer_reference,
                "payment_evidence_mode": (
                    "corporate_transfer_reference"
                    if has_corporate_transfer_reference and not has_payment_record
                    else "payment_record"
                ),
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
            "corporate_transfer_reference": invoice.corporate_transfer_reference,
            "payment_evidence_mode": "missing",
        },
    )


def validate_paper_invoice_receipt_requirement(
    invoice: InvoiceRecord,
) -> ValidationResult:
    if not invoice.is_paper_invoice:
        return _validation_result(
            rule_code=PAPER_INVOICE_RECEIPT_REQUIRED_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="当前不是纸质发票，无需确认收票",
            evidence={
                "is_paper_invoice": False,
                "paper_invoice_received": invoice.paper_invoice_received,
                "paper_invoice_received_at": (
                    invoice.paper_invoice_received_at.isoformat()
                    if invoice.paper_invoice_received_at is not None
                    else None
                ),
                "paper_invoice_received_by": invoice.paper_invoice_received_by,
            },
        )
    if invoice.paper_invoice_received:
        return _validation_result(
            rule_code=PAPER_INVOICE_RECEIPT_REQUIRED_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message="纸质发票已由管理员确认收到",
            evidence={
                "is_paper_invoice": True,
                "paper_invoice_received": True,
                "paper_invoice_received_at": (
                    invoice.paper_invoice_received_at.isoformat()
                    if invoice.paper_invoice_received_at is not None
                    else None
                ),
                "paper_invoice_received_by": invoice.paper_invoice_received_by,
            },
        )
    return _validation_result(
        rule_code=PAPER_INVOICE_RECEIPT_REQUIRED_RULE_CODE,
        target_id=invoice.id,
        status=ValidationStatus.FAILED,
        message="纸质发票待管理员确认已收到纸票",
        evidence={
            "is_paper_invoice": True,
            "paper_invoice_received": False,
            "paper_invoice_received_at": None,
            "paper_invoice_received_by": None,
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
    has_corporate_transfer_reference = bool(invoice.corporate_transfer_reference)
    evidence = {
        "invoice_amount_cents": invoice.amount_cents,
        "threshold_amount_cents": threshold_cents,
        "matching_mode": PAYMENT_RECORD_AMOUNT_MATCH_MODE,
        "config_source": (
            "trms_backend.domain.invoice_validation.PAYMENT_RECORD_AMOUNT_MATCH_MODE"
        ),
        "requires_payment_record": requires_payment_record,
        "payment_record_material_ids": payment_record_material_ids,
        "corporate_transfer_reference": invoice.corporate_transfer_reference,
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

    if has_corporate_transfer_reference and not payment_record_material_ids:
        return _validation_result(
            rule_code=PAYMENT_RECORD_AMOUNT_MATCH_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="已填写公对公转账编号，暂不执行支付记录金额匹配",
            evidence=evidence | {"matching_mode": "corporate_transfer_reference_exempt"},
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


def validate_competition_notice_requirement(
    invoice: InvoiceRecord,
    supporting_materials: list[MaterialRecord],
) -> ValidationResult:
    competition_notice_material_ids = [
        material.id
        for material in supporting_materials
        if material.material_type is MaterialType.COMPETITION_NOTICE
    ]
    requires_competition_notice = invoice.expense_type is ExpenseType.REGISTRATION
    evidence = {
        "expense_type": invoice.expense_type.value,
        "required_material_type": MaterialType.COMPETITION_NOTICE.value,
        "requires_competition_notice": requires_competition_notice,
        "competition_notice_material_ids": competition_notice_material_ids,
    }

    if not requires_competition_notice:
        return _validation_result(
            rule_code=COMPETITION_NOTICE_REQUIRED_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="当前费用类型不要求比赛通知",
            evidence=evidence,
        )

    if competition_notice_material_ids:
        return _validation_result(
            rule_code=COMPETITION_NOTICE_REQUIRED_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message="参赛费已关联比赛通知",
            evidence=evidence,
        )

    return _validation_result(
        rule_code=COMPETITION_NOTICE_REQUIRED_RULE_CODE,
        target_id=invoice.id,
        status=ValidationStatus.FAILED,
        message="参赛费缺少比赛通知",
        evidence=evidence,
    )


def validate_airfare_itinerary_requirement(
    invoice: InvoiceRecord,
    supporting_materials: list[MaterialRecord],
    recognition_task: RecognitionTaskRecord | None = None,
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None] | None = None,
) -> ValidationResult:
    supporting_material_recognitions = supporting_material_recognitions or {}
    itinerary_material_ids = [
        material.id
        for material in supporting_materials
        if material.material_type is MaterialType.ITINERARY
    ]
    requires_itinerary = invoice.expense_type is ExpenseType.AIRFARE
    recognized_airport_code_materials = _collect_airfare_airport_code_evidence(
        invoice,
        recognition_task,
        supporting_materials,
        supporting_material_recognitions,
    )
    evidence = {
        "expense_type": invoice.expense_type.value,
        "invoice_material_id": invoice.material_id,
        "required_material_type": MaterialType.ITINERARY.value,
        "requires_itinerary": requires_itinerary,
        "invoice_material_present": True,
        "itinerary_material_ids": itinerary_material_ids,
    }
    if recognized_airport_code_materials:
        evidence["airport_code_field_groups"] = [
            list(group) for group in AIRFARE_AIRPORT_CODE_FIELD_GROUPS
        ]
        evidence["recognized_airport_code_materials"] = recognized_airport_code_materials

    if not requires_itinerary:
        return _validation_result(
            rule_code=AIRFARE_ITINERARY_REQUIRED_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="当前费用类型不要求航空行程单",
            evidence=evidence,
        )

    if itinerary_material_ids:
        return _validation_result(
            rule_code=AIRFARE_ITINERARY_REQUIRED_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message="航空费用已关联行程单",
            evidence=evidence,
        )

    if recognized_airport_code_materials:
        return _validation_result(
            rule_code=AIRFARE_ITINERARY_REQUIRED_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message="航空费用已具备往返机场代码，无需补充行程单",
            evidence=evidence,
        )

    return _validation_result(
        rule_code=AIRFARE_ITINERARY_REQUIRED_RULE_CODE,
        target_id=invoice.id,
        status=ValidationStatus.FAILED,
        message="航空费用缺少行程单",
        evidence=evidence,
    )


def validate_airfare_cabin_requirement(
    invoice: InvoiceRecord,
    recognition_task: RecognitionTaskRecord | None,
    supporting_materials: list[MaterialRecord],
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None],
) -> ValidationResult:
    itinerary_material_ids = [
        material.id
        for material in supporting_materials
        if material.material_type is MaterialType.ITINERARY
    ]
    order_screenshot_material_ids = [
        material.id
        for material in supporting_materials
        if material.material_type is MaterialType.ORDER_SCREENSHOT
    ]
    requires_cabin_proof = invoice.expense_type is ExpenseType.AIRFARE
    recognized_cabin_materials = _collect_airfare_cabin_evidence(
        invoice,
        recognition_task,
        supporting_materials,
        supporting_material_recognitions,
    )
    recognized_airport_code_materials = _collect_airfare_airport_code_evidence(
        invoice,
        recognition_task,
        supporting_materials,
        supporting_material_recognitions,
    )
    evidence = {
        "expense_type": invoice.expense_type.value,
        "invoice_material_id": invoice.material_id,
        "cabin_field_names": list(AIRFARE_CABIN_FIELD_NAMES),
        "airport_code_field_groups": [list(group) for group in AIRFARE_AIRPORT_CODE_FIELD_GROUPS],
        "requires_cabin_proof": requires_cabin_proof,
        "itinerary_material_ids": itinerary_material_ids,
        "order_screenshot_material_ids": order_screenshot_material_ids,
        "recognized_cabin_materials": recognized_cabin_materials,
        "recognized_airport_code_materials": recognized_airport_code_materials,
    }

    if not requires_cabin_proof:
        return _validation_result(
            rule_code=AIRFARE_CABIN_PROOF_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="当前费用类型不要求航空舱位校验",
            evidence=evidence,
        )

    if recognized_cabin_materials:
        return _validation_result(
            rule_code=AIRFARE_CABIN_PROOF_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message="航空费用已具备舱位信息",
            evidence=evidence,
        )

    if recognized_airport_code_materials:
        return _validation_result(
            rule_code=AIRFARE_CABIN_PROOF_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message="航空费用已具备往返机场代码，无需补充订单截图",
            evidence=evidence,
        )

    if order_screenshot_material_ids:
        return _validation_result(
            rule_code=AIRFARE_CABIN_PROOF_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PENDING,
            message="航空费用未识别到舱位信息，需结合订单截图人工确认",
            evidence=evidence,
        )

    return _validation_result(
        rule_code=AIRFARE_CABIN_PROOF_RULE_CODE,
        target_id=invoice.id,
        status=ValidationStatus.FAILED,
        message="航空费用缺少舱位信息，且未关联订单截图",
        evidence=evidence,
    )


def validate_local_transport_rideshare_trip_requirement(
    invoice: InvoiceRecord,
    recognition_task: RecognitionTaskRecord | None,
    supporting_materials: list[MaterialRecord],
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None],
) -> ValidationResult:
    requires_local_transport_validation = invoice.expense_type is ExpenseType.LOCAL_TRANSPORT
    rideshare_detections = _collect_rideshare_detections(
        invoice,
        recognition_task,
        supporting_materials,
        supporting_material_recognitions,
    )
    if requires_local_transport_validation and _is_local_transport_electronic_invoice(
        recognition_task
    ):
        rideshare_detections.append(
            {
                "material_id": invoice.material_id,
                "material_type": MaterialType.INVOICE.value,
                "field_name": "local_transport_electronic_invoice_policy",
                "field_value": "local_transport_invoice_requires_rideshare_trip",
                "is_rideshare": True,
                "recognition_task_id": recognition_task.id if recognition_task is not None else None,
                "recognition_task_status": (
                    recognition_task.status.value if recognition_task is not None else None
                ),
            }
        )
    trip_information_materials = _collect_trip_information_materials(
        invoice,
        recognition_task,
        supporting_materials,
        supporting_material_recognitions,
    )
    evidence = {
        "expense_type": invoice.expense_type.value,
        "invoice_material_id": invoice.material_id,
        "rideshare_indicator_field_names": list(RIDESHARE_INDICATOR_FIELD_NAMES),
        "trip_field_groups": [list(group) for group in RIDESHARE_TRIP_FIELD_GROUPS],
        "requires_local_transport_validation": requires_local_transport_validation,
        "rideshare_detections": rideshare_detections,
        "trip_information_materials": trip_information_materials,
    }

    if not requires_local_transport_validation:
        return _validation_result(
            rule_code=LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="当前费用类型不要求网约车行程信息校验",
            evidence=evidence,
        )

    rideshare_decision = _decide_rideshare_requirement(rideshare_detections)
    if rideshare_decision is None:
        return _validation_result(
            rule_code=LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PENDING,
            message="市内交通无法判断是否为网约车，需人工确认",
            evidence=evidence,
        )

    if rideshare_decision is False:
        return _validation_result(
            rule_code=LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="当前市内交通识别结果显示非网约车，无需补充行程信息",
            evidence=evidence,
        )

    if trip_information_materials:
        return _validation_result(
            rule_code=LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message="网约车费用已具备行程信息",
            evidence=evidence,
        )

    return _validation_result(
        rule_code=LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
        target_id=invoice.id,
        status=ValidationStatus.FAILED,
        message="网约车费用缺少行程信息",
        evidence=evidence,
    )


def validate_competition_time_range(
    invoice: InvoiceRecord,
    task: ReimbursementTask,
) -> ValidationResult:
    requires_competition_time_validation = (
        invoice.expense_type in COMPETITION_TIME_SUPPORTED_EXPENSE_TYPES
    )
    effective_start_date = task.competition_start_date - timedelta(
        days=COMPETITION_TIME_BUFFER_DAYS_BEFORE
    )
    effective_end_date = task.competition_end_date + timedelta(
        days=COMPETITION_TIME_BUFFER_DAYS_AFTER
    )
    transaction_date = _extract_transaction_date(invoice.transaction_time)
    evidence = {
        "expense_type": invoice.expense_type.value,
        "supported_expense_types": [
            expense_type.value for expense_type in COMPETITION_TIME_SUPPORTED_EXPENSE_TYPES
        ],
        "requires_competition_time_validation": requires_competition_time_validation,
        "competition_start_date": task.competition_start_date.isoformat(),
        "competition_end_date": task.competition_end_date.isoformat(),
        "buffer_days_before": COMPETITION_TIME_BUFFER_DAYS_BEFORE,
        "buffer_days_after": COMPETITION_TIME_BUFFER_DAYS_AFTER,
        "effective_start_date": effective_start_date.isoformat(),
        "effective_end_date": effective_end_date.isoformat(),
        "transaction_time": (
            invoice.transaction_time.isoformat() if invoice.transaction_time is not None else None
        ),
        "transaction_date": transaction_date.isoformat() if transaction_date is not None else None,
        "issue_date": invoice.issue_date.isoformat() if invoice.issue_date is not None else None,
        "time_source": (
            "transaction_time" if invoice.transaction_time is not None else "missing_transaction_time"
        ),
    }

    return _validation_result(
        rule_code=COMPETITION_TIME_RANGE_RULE_CODE,
        target_id=invoice.id,
        status=ValidationStatus.NOT_APPLICABLE,
        message="当前不限制发票交易产生时间",
        evidence=evidence,
        severity=ValidationSeverity.WARNING,
    )


def validate_competition_location_range(
    invoice: InvoiceRecord,
    task: ReimbursementTask,
    recognition_task: RecognitionTaskRecord | None,
    supporting_materials: list[MaterialRecord],
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None],
) -> ValidationResult:
    requires_competition_location_validation = (
        invoice.expense_type in COMPETITION_LOCATION_SUPPORTED_EXPENSE_TYPES
    )
    location_candidates = _collect_competition_location_candidates(
        invoice,
        recognition_task,
        supporting_materials,
        supporting_material_recognitions,
        task.competition_location,
    )
    matched_location_materials = [
        item for item in location_candidates if item["competition_location_match"] is True
    ]
    unmatched_location_materials = [
        item for item in location_candidates if item["competition_location_match"] is False
    ]
    evidence = {
        "expense_type": invoice.expense_type.value,
        "supported_expense_types": [
            expense_type.value for expense_type in COMPETITION_LOCATION_SUPPORTED_EXPENSE_TYPES
        ],
        "requires_competition_location_validation": requires_competition_location_validation,
        "competition_location": task.competition_location,
        "location_field_groups": [list(group) for group in COMPETITION_LOCATION_FIELD_GROUPS],
        "matched_location_materials": matched_location_materials,
        "unmatched_location_materials": unmatched_location_materials,
    }

    if not requires_competition_location_validation:
        return _validation_result(
            rule_code=COMPETITION_LOCATION_RANGE_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.NOT_APPLICABLE,
            message="当前费用类型不要求比赛地点范围校验",
            evidence=evidence,
            severity=ValidationSeverity.WARNING,
        )

    if not location_candidates:
        return _validation_result(
            rule_code=COMPETITION_LOCATION_RANGE_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PENDING,
            message="缺少可用于比赛地点范围校验的地点信息，需人工确认",
            evidence=evidence,
            severity=ValidationSeverity.WARNING,
        )

    if matched_location_materials:
        return _validation_result(
            rule_code=COMPETITION_LOCATION_RANGE_RULE_CODE,
            target_id=invoice.id,
            status=ValidationStatus.PASSED,
            message="交易地点与比赛地点或往返路径基础匹配",
            evidence=evidence,
            severity=ValidationSeverity.WARNING,
        )

    return _validation_result(
        rule_code=COMPETITION_LOCATION_RANGE_RULE_CODE,
        target_id=invoice.id,
        status=ValidationStatus.FAILED,
        message="交易地点与比赛地点或往返路径不匹配，需人工确认",
        evidence=evidence,
        severity=ValidationSeverity.WARNING,
    )


def _extract_transaction_date(transaction_time: datetime | None) -> date | None:
    if transaction_time is None:
        return None
    return transaction_time.date()


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


def _collect_airfare_cabin_evidence(
    invoice: InvoiceRecord,
    recognition_task: RecognitionTaskRecord | None,
    supporting_materials: list[MaterialRecord],
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None],
) -> list[dict[str, object | None]]:
    recognized_cabin_materials: list[dict[str, object | None]] = []

    primary_material_match = _extract_recognized_field_match(
        recognition_task,
        AIRFARE_CABIN_FIELD_NAMES,
    )
    if primary_material_match is not None:
        recognized_cabin_materials.append(
            {
                "material_id": invoice.material_id,
                "material_type": MaterialType.INVOICE.value,
                **primary_material_match,
            }
        )

    for material in supporting_materials:
        if material.material_type not in {MaterialType.ITINERARY, MaterialType.ORDER_SCREENSHOT}:
            continue
        field_match = _extract_recognized_field_match(
            supporting_material_recognitions.get(material.id),
            AIRFARE_CABIN_FIELD_NAMES,
        )
        if field_match is None:
            continue
        recognized_cabin_materials.append(
            {
                "material_id": material.id,
                "material_type": material.material_type.value,
                **field_match,
            }
        )

    return recognized_cabin_materials


def _collect_airfare_airport_code_evidence(
    invoice: InvoiceRecord,
    recognition_task: RecognitionTaskRecord | None,
    supporting_materials: list[MaterialRecord],
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None],
) -> list[dict[str, object | None]]:
    recognized_airport_code_materials: list[dict[str, object | None]] = []

    primary_material_match = _extract_airport_code_group_match(
        material_id=invoice.material_id,
        material_type=MaterialType.INVOICE,
        recognition_task=recognition_task,
    )
    if primary_material_match is not None:
        recognized_airport_code_materials.append(primary_material_match)

    for material in supporting_materials:
        if material.material_type not in {MaterialType.ITINERARY, MaterialType.ORDER_SCREENSHOT}:
            continue
        field_match = _extract_airport_code_group_match(
            material_id=material.id,
            material_type=material.material_type,
            recognition_task=supporting_material_recognitions.get(material.id),
        )
        if field_match is None:
            continue
        recognized_airport_code_materials.append(field_match)

    return recognized_airport_code_materials


def _extract_airport_code_group_match(
    *,
    material_id: str,
    material_type: MaterialType,
    recognition_task: RecognitionTaskRecord | None,
) -> dict[str, object | None] | None:
    if recognition_task is None:
        return None
    for field_group in AIRFARE_AIRPORT_CODE_FIELD_GROUPS:
        matched_values = _extract_field_group_values(recognition_task, field_group)
        if not matched_values:
            continue
        return {
            "material_id": material_id,
            "material_type": material_type.value,
            "matched_fields": matched_values,
            "recognition_task_id": recognition_task.id,
            "recognition_task_status": recognition_task.status.value,
        }
    return None


def _extract_recognized_field_match(
    recognition_task: RecognitionTaskRecord | None,
    field_names: tuple[str, ...],
) -> dict[str, object | None] | None:
    if recognition_task is None:
        return None
    for field_name in field_names:
        field_result = recognition_task.recognized_fields.get(field_name)
        if field_result is None or not _has_meaningful_field_value(field_result.value):
            continue
        return {
            "field_name": field_name,
            "field_value": field_result.value,
            "recognition_task_id": recognition_task.id,
            "recognition_task_status": recognition_task.status.value,
        }
    return None


def _collect_rideshare_detections(
    invoice: InvoiceRecord,
    recognition_task: RecognitionTaskRecord | None,
    supporting_materials: list[MaterialRecord],
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None],
) -> list[dict[str, object | None]]:
    detections: list[dict[str, object | None]] = []

    primary_detection = _extract_rideshare_detection(
        material_id=invoice.material_id,
        material_type=MaterialType.INVOICE,
        recognition_task=recognition_task,
    )
    if primary_detection is not None:
        detections.append(primary_detection)

    for material in supporting_materials:
        detection = _extract_rideshare_detection(
            material_id=material.id,
            material_type=material.material_type,
            recognition_task=supporting_material_recognitions.get(material.id),
        )
        if detection is not None:
            detections.append(detection)

    return detections


def _extract_rideshare_detection(
    *,
    material_id: str,
    material_type: MaterialType,
    recognition_task: RecognitionTaskRecord | None,
) -> dict[str, object | None] | None:
    if recognition_task is None:
        return None
    for field_name in RIDESHARE_INDICATOR_FIELD_NAMES:
        field_result = recognition_task.recognized_fields.get(field_name)
        if field_result is None:
            continue
        normalized = _normalize_rideshare_indicator_value(field_result.value)
        if normalized is None:
            continue
        return {
            "material_id": material_id,
            "material_type": material_type.value,
            "field_name": field_name,
            "field_value": field_result.value,
            "is_rideshare": normalized,
            "recognition_task_id": recognition_task.id,
            "recognition_task_status": recognition_task.status.value,
        }
    return None


def _normalize_rideshare_indicator_value(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in RIDESHARE_TRUE_VALUES:
            return True
        if normalized in RIDESHARE_FALSE_VALUES:
            return False
    return None


def _decide_rideshare_requirement(
    rideshare_detections: list[dict[str, object | None]],
) -> bool | None:
    if not rideshare_detections:
        return None
    rideshare_values = {
        item["is_rideshare"]
        for item in rideshare_detections
        if isinstance(item.get("is_rideshare"), bool)
    }
    if True in rideshare_values:
        return True
    if rideshare_values == {False}:
        return False
    return None


def _is_local_transport_electronic_invoice(
    recognition_task: RecognitionTaskRecord | None,
) -> bool:
    if recognition_task is None:
        return False
    for field_name in ("material_type", "document_family"):
        field_result = recognition_task.recognized_fields.get(field_name)
        if field_result is None:
            continue
        if field_result.value == MaterialType.INVOICE.value:
            return True
    return False


def _collect_trip_information_materials(
    invoice: InvoiceRecord,
    recognition_task: RecognitionTaskRecord | None,
    supporting_materials: list[MaterialRecord],
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None],
) -> list[dict[str, object | None]]:
    trip_information_materials: list[dict[str, object | None]] = []

    primary_material_trip_info = _extract_trip_information_match(
        material_id=invoice.material_id,
        material_type=MaterialType.INVOICE,
        recognition_task=recognition_task,
    )
    if primary_material_trip_info is not None:
        trip_information_materials.append(primary_material_trip_info)

    for material in supporting_materials:
        trip_info = _extract_trip_information_match(
            material_id=material.id,
            material_type=material.material_type,
            recognition_task=supporting_material_recognitions.get(material.id),
        )
        if trip_info is not None:
            trip_information_materials.append(trip_info)

    return trip_information_materials


def _extract_trip_information_match(
    *,
    material_id: str,
    material_type: MaterialType,
    recognition_task: RecognitionTaskRecord | None,
) -> dict[str, object | None] | None:
    if recognition_task is None:
        return None
    for field_group in RIDESHARE_TRIP_FIELD_GROUPS:
        matched_values: dict[str, object] = {}
        for field_name in field_group:
            field_result = recognition_task.recognized_fields.get(field_name)
            if field_result is None or not _has_meaningful_field_value(field_result.value):
                matched_values = {}
                break
            matched_values[field_name] = field_result.value
        if not matched_values:
            continue
        return {
            "material_id": material_id,
            "material_type": material_type.value,
            "matched_fields": matched_values,
            "recognition_task_id": recognition_task.id,
            "recognition_task_status": recognition_task.status.value,
        }
    return None


def _collect_competition_location_candidates(
    invoice: InvoiceRecord,
    recognition_task: RecognitionTaskRecord | None,
    supporting_materials: list[MaterialRecord],
    supporting_material_recognitions: dict[str, RecognitionTaskRecord | None],
    competition_location: str,
) -> list[dict[str, object | None]]:
    candidates: list[dict[str, object | None]] = []

    primary_candidate = _extract_competition_location_candidate(
        material_id=invoice.material_id,
        material_type=MaterialType.INVOICE,
        recognition_task=recognition_task,
        competition_location=competition_location,
    )
    if primary_candidate is not None:
        candidates.append(primary_candidate)

    for material in supporting_materials:
        candidate = _extract_competition_location_candidate(
            material_id=material.id,
            material_type=material.material_type,
            recognition_task=supporting_material_recognitions.get(material.id),
            competition_location=competition_location,
        )
        if candidate is not None:
            candidates.append(candidate)

    return candidates


def _extract_competition_location_candidate(
    *,
    material_id: str,
    material_type: MaterialType,
    recognition_task: RecognitionTaskRecord | None,
    competition_location: str,
) -> dict[str, object | None] | None:
    if recognition_task is None:
        return None

    first_available_candidate: dict[str, object | None] | None = None
    for field_group in COMPETITION_LOCATION_FIELD_GROUPS:
        matched_values = _extract_field_group_values(recognition_task, field_group)
        if not matched_values:
            continue
        candidate = {
            "material_id": material_id,
            "material_type": material_type.value,
            "matched_fields": matched_values,
            "competition_location_match": _competition_location_matches_group(
                competition_location,
                matched_values,
            ),
            "recognition_task_id": recognition_task.id,
            "recognition_task_status": recognition_task.status.value,
        }
        if candidate["competition_location_match"] is True:
            return candidate
        if first_available_candidate is None:
            first_available_candidate = candidate
    return first_available_candidate


def _extract_field_group_values(
    recognition_task: RecognitionTaskRecord,
    field_group: tuple[str, ...],
) -> dict[str, object]:
    matched_values: dict[str, object] = {}
    for field_name in field_group:
        field_result = recognition_task.recognized_fields.get(field_name)
        if field_result is None or not _has_meaningful_field_value(field_result.value):
            return {}
        matched_values[field_name] = field_result.value
    return matched_values


def _competition_location_matches_group(
    competition_location: str,
    field_values: dict[str, object],
) -> bool:
    return any(
        _competition_location_matches_value(competition_location, field_value)
        for field_value in field_values.values()
    )


def _competition_location_matches_value(
    competition_location: str,
    value: object,
) -> bool:
    if not isinstance(value, str):
        return False
    normalized_competition_location = _normalize_location_text(competition_location)
    normalized_value = _normalize_location_text(value)
    if not normalized_competition_location or not normalized_value:
        return False
    return (
        normalized_competition_location in normalized_value
        or normalized_value in normalized_competition_location
    )


def _normalize_location_text(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _has_meaningful_field_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return value
    return True
