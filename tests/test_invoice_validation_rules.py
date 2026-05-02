from datetime import date, datetime, timezone

import pytest

from trms_backend.domain.invoice_validation import (
    AIRFARE_CABIN_PROOF_RULE_CODE,
    AIRFARE_ITINERARY_REQUIRED_RULE_CODE,
    COMPETITION_LOCATION_RANGE_RULE_CODE,
    COMPETITION_NOTICE_REQUIRED_RULE_CODE,
    COMPETITION_TIME_RANGE_RULE_CODE,
    LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
    PAPER_INVOICE_RECEIPT_REQUIRED_RULE_CODE,
    PAYMENT_RECORD_AMOUNT_MATCH_RULE_CODE,
    PAYMENT_RECORD_REQUIRED_RULE_CODE,
    validate_airfare_cabin_requirement,
    validate_airfare_itinerary_requirement,
    validate_competition_location_range,
    validate_competition_notice_requirement,
    validate_competition_time_range,
    validate_invoice,
    validate_local_transport_rideshare_trip_requirement,
    validate_paper_invoice_receipt_requirement,
    validate_payment_record_amount_match,
    validate_payment_record_requirement,
)
from trms_backend.domain.invoices import ExpenseType, InvoiceRecord, ValidationStatus
from trms_backend.domain.materials import MaterialRecord, MaterialStatus, MaterialType, SubmissionChannel
from trms_backend.domain.recognitions import (
    RecognitionFieldResult,
    RecognitionFieldSource,
    RecognitionTaskRecord,
    RecognitionTaskStatus,
)
from trms_backend.domain.tasks import ReimbursementTask, TaskStatus

NOW = datetime(2026, 4, 29, 4, 30, tzinfo=timezone.utc)


def make_task() -> ReimbursementTask:
    return ReimbursementTask(
        id="task-1",
        status=TaskStatus.OPEN,
        competition_name="CCPC",
        competition_location="Shanghai",
        competition_start_date=date(2026, 5, 1),
        competition_end_date=date(2026, 5, 3),
        deadline=datetime(2026, 5, 10, tzinfo=timezone.utc),
        member_ids=["2250001", "2250002"],
        fee_categories=[
            ExpenseType.REGISTRATION.value,
            ExpenseType.RAILWAY.value,
            ExpenseType.AIRFARE.value,
            ExpenseType.LOCAL_TRANSPORT.value,
            ExpenseType.HOTEL.value,
        ],
        administrator_ids=["admin-1"],
        administrator_id="admin-1",
        project_info="ACM",
        reimburser_info="Lab",
        invoice_title="同济大学",
        tax_number="12100000425006117D",
        created_at=NOW,
        updated_at=NOW,
    )


def make_invoice(
    *,
    invoice_id: str = "invoice-1",
    material_id: str = "material-invoice",
    buyer_name: str = "同济大学",
    tax_number: str = "12100000425006117D",
    amount_cents: int = 150_000,
    expense_type: ExpenseType = ExpenseType.RAILWAY,
    transaction_time: datetime | None = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc),
) -> InvoiceRecord:
    return InvoiceRecord(
        id=invoice_id,
        task_id="task-1",
        material_id=material_id,
        invoice_number="INV-001",
        issue_date=date(2026, 5, 1),
        transaction_time=transaction_time,
        buyer_name=buyer_name,
        tax_number=tax_number,
        seller_name="供应商",
        corporate_transfer_reference=None,
        amount_cents=amount_cents,
        expense_type=expense_type,
        created_at=NOW,
        updated_at=NOW,
    )


def make_material(
    material_id: str,
    *,
    material_type: MaterialType,
    content_type: str = "application/pdf",
) -> MaterialRecord:
    return MaterialRecord(
        id=material_id,
        status=MaterialStatus.ASSIGNED,
        task_id="task-1",
        submitter_id="2250001",
        task_id_hint=None,
        submitter_id_hint=None,
        channel=SubmissionChannel.WEB,
        material_type=material_type,
        storage_key=f"{material_id}.bin",
        original_filename=f"{material_id}.bin",
        content_type=content_type,
        size_bytes=128,
        sha256=material_id.rjust(64, "0")[:64],
        duplicate_of=None,
        claimed_by=None,
        claimed_at=None,
        created_at=NOW,
    )


def make_recognition(
    material_id: str,
    *,
    recognition_id: str | None = None,
    status: RecognitionTaskStatus = RecognitionTaskStatus.SUCCEEDED,
    recognized_fields: dict[str, object] | None = None,
) -> RecognitionTaskRecord:
    fields = {
        field_name: RecognitionFieldResult(
            value=value,
            source=RecognitionFieldSource.AI,
            confidence=0.98,
        )
        for field_name, value in (recognized_fields or {}).items()
    }
    return RecognitionTaskRecord(
        id=recognition_id or f"recognition-{material_id}",
        material_id=material_id,
        status=status,
        raw_response={"provider": "test"},
        recognized_fields=fields,
        manual_corrections=[],
        created_at=NOW,
        updated_at=NOW,
    )


def result_by_code(results, rule_code: str):
    return next(result for result in results if result.rule_code == rule_code)


@pytest.mark.parametrize(
    ("buyer_name", "tax_number", "recognition_task", "expected_status"),
    [
        ("同济大学", "12100000425006117D", None, ValidationStatus.PASSED),
        ("其他单位", "WRONG-TAX", None, ValidationStatus.FAILED),
        (
            "同济大学",
            "12100000425006117D",
            make_recognition("material-invoice", recognized_fields={"seller_name": "供应商"}),
            ValidationStatus.PENDING,
        ),
    ],
)
def test_invoice_title_and_tax_number_rules_cover_passed_failed_pending_paths(
    buyer_name: str,
    tax_number: str,
    recognition_task: RecognitionTaskRecord | None,
    expected_status: ValidationStatus,
):
    results = validate_invoice(
        make_invoice(buyer_name=buyer_name, tax_number=tax_number),
        make_task(),
        duplicate_invoice_id=None,
        recognition_task=recognition_task,
    )

    assert result_by_code(results, "invoice_title_match").status is expected_status
    assert result_by_code(results, "invoice_tax_number_match").status is expected_status


@pytest.mark.parametrize(
    ("duplicate_invoice_id", "expected_status"),
    [
        (None, ValidationStatus.PASSED),
        ("invoice-2", ValidationStatus.FAILED),
    ],
)
def test_duplicate_invoice_rule_covers_passed_and_failed_paths(
    duplicate_invoice_id: str | None,
    expected_status: ValidationStatus,
):
    results = validate_invoice(
        make_invoice(),
        make_task(),
        duplicate_invoice_id=duplicate_invoice_id,
    )

    duplicate_validation = result_by_code(results, "invoice_number_unique")
    assert duplicate_validation.status is expected_status
    assert duplicate_validation.evidence["duplicate_invoice_id"] == duplicate_invoice_id


def test_invoice_validation_no_longer_emits_competition_location_range_rule():
    results = validate_invoice(
        make_invoice(expense_type=ExpenseType.RAILWAY),
        make_task(),
        duplicate_invoice_id=None,
        recognition_task=make_recognition(
            "material-invoice",
            recognized_fields={
                "departure_location": "Nanjing South Railway Station",
                "arrival_location": "Suzhou Railway Station",
            },
        ),
    )

    rule_codes = [result.rule_code for result in results]
    assert COMPETITION_LOCATION_RANGE_RULE_CODE not in rule_codes


@pytest.mark.parametrize(
    ("supporting_materials", "expected_status"),
    [
        ([], ValidationStatus.FAILED),
        (
            [make_material("payment-1", material_type=MaterialType.PAYMENT_RECORD, content_type="image/png")],
            ValidationStatus.PASSED,
        ),
    ],
)
def test_payment_record_requirement_rule_covers_passed_and_failed_paths(
    supporting_materials: list[MaterialRecord],
    expected_status: ValidationStatus,
):
    result = validate_payment_record_requirement(make_invoice(), supporting_materials)

    assert result.rule_code == PAYMENT_RECORD_REQUIRED_RULE_CODE
    assert result.status is expected_status


def test_payment_record_requirement_rule_passes_with_corporate_transfer_reference():
    invoice = make_invoice()
    invoice.corporate_transfer_reference = "ABC123456789"

    result = validate_payment_record_requirement(invoice, [])

    assert result.rule_code == PAYMENT_RECORD_REQUIRED_RULE_CODE
    assert result.status is ValidationStatus.PASSED
    assert result.message == "发票金额达到阈值，已填写公对公转账编号"
    assert result.evidence["corporate_transfer_reference"] == "ABC123456789"
    assert result.evidence["payment_evidence_mode"] == "corporate_transfer_reference"


@pytest.mark.parametrize(
    ("recognitions", "expected_status"),
    [
        (
            {"payment-1": make_recognition("payment-1", recognized_fields={"amount_cents": 150_000})},
            ValidationStatus.PASSED,
        ),
        (
            {"payment-1": make_recognition("payment-1", recognized_fields={"amount_cents": 149_999})},
            ValidationStatus.FAILED,
        ),
        (
            {"payment-1": make_recognition("payment-1", recognized_fields={"seller_name": "支付宝"})},
            ValidationStatus.PENDING,
        ),
    ],
)
def test_payment_record_amount_match_rule_covers_passed_failed_pending_paths(
    recognitions: dict[str, RecognitionTaskRecord],
    expected_status: ValidationStatus,
):
    payment_record = make_material(
        "payment-1",
        material_type=MaterialType.PAYMENT_RECORD,
        content_type="image/png",
    )

    result = validate_payment_record_amount_match(
        make_invoice(),
        [payment_record],
        recognitions,
    )

    assert result.rule_code == PAYMENT_RECORD_AMOUNT_MATCH_RULE_CODE
    assert result.status is expected_status


def test_payment_record_amount_match_rule_is_not_applicable_with_corporate_transfer_reference():
    invoice = make_invoice()
    invoice.corporate_transfer_reference = "ABC123456789"

    result = validate_payment_record_amount_match(
        invoice,
        [],
        {},
    )

    assert result.rule_code == PAYMENT_RECORD_AMOUNT_MATCH_RULE_CODE
    assert result.status is ValidationStatus.NOT_APPLICABLE
    assert result.message == "已填写公对公转账编号，暂不执行支付记录金额匹配"
    assert result.evidence["matching_mode"] == "corporate_transfer_reference_exempt"


def test_paper_invoice_receipt_requirement_blocks_until_admin_confirms_receipt():
    invoice = make_invoice()
    invoice.is_paper_invoice = True

    result = validate_paper_invoice_receipt_requirement(invoice)

    assert result.rule_code == PAPER_INVOICE_RECEIPT_REQUIRED_RULE_CODE
    assert result.status is ValidationStatus.FAILED
    assert result.message == "纸质发票待管理员确认已收到纸票"


def test_paper_invoice_receipt_requirement_passes_after_admin_confirms_receipt():
    invoice = make_invoice()
    invoice.is_paper_invoice = True
    invoice.paper_invoice_received = True
    invoice.paper_invoice_received_at = NOW
    invoice.paper_invoice_received_by = "admin-1"

    result = validate_paper_invoice_receipt_requirement(invoice)

    assert result.rule_code == PAPER_INVOICE_RECEIPT_REQUIRED_RULE_CODE
    assert result.status is ValidationStatus.PASSED
    assert result.message == "纸质发票已由管理员确认收到"
    assert result.evidence["paper_invoice_received_by"] == "admin-1"


def test_paper_invoice_skips_local_transport_rideshare_trip_requirement():
    invoice = make_invoice(expense_type=ExpenseType.LOCAL_TRANSPORT)
    invoice.is_paper_invoice = True

    result = validate_local_transport_rideshare_trip_requirement(
        invoice,
        recognition_task=None,
        supporting_materials=[],
        supporting_material_recognitions={},
    )

    assert result.rule_code == LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE
    assert result.status is ValidationStatus.NOT_APPLICABLE
    assert result.message == "纸质发票暂不执行网约车行程信息校验"
    assert result.evidence["is_paper_invoice"] is True


@pytest.mark.parametrize(
    ("supporting_materials", "expected_status"),
    [
        ([], ValidationStatus.FAILED),
        (
            [make_material("notice-1", material_type=MaterialType.COMPETITION_NOTICE)],
            ValidationStatus.PASSED,
        ),
    ],
)
def test_competition_notice_rule_covers_passed_and_failed_paths(
    supporting_materials: list[MaterialRecord],
    expected_status: ValidationStatus,
):
    result = validate_competition_notice_requirement(
        make_invoice(expense_type=ExpenseType.REGISTRATION),
        supporting_materials,
    )

    assert result.rule_code == COMPETITION_NOTICE_REQUIRED_RULE_CODE
    assert result.status is expected_status


@pytest.mark.parametrize(
    ("supporting_materials", "expected_status"),
    [
        ([], ValidationStatus.FAILED),
        (
            [make_material("itinerary-1", material_type=MaterialType.ITINERARY)],
            ValidationStatus.PASSED,
        ),
    ],
)
def test_airfare_itinerary_rule_covers_passed_and_failed_paths(
    supporting_materials: list[MaterialRecord],
    expected_status: ValidationStatus,
):
    result = validate_airfare_itinerary_requirement(
        make_invoice(expense_type=ExpenseType.AIRFARE),
        supporting_materials,
    )

    assert result.rule_code == AIRFARE_ITINERARY_REQUIRED_RULE_CODE
    assert result.status is expected_status


def test_airfare_itinerary_rule_passes_when_invoice_has_airport_codes():
    result = validate_airfare_itinerary_requirement(
        make_invoice(expense_type=ExpenseType.AIRFARE),
        [],
        recognition_task=make_recognition(
            "material-invoice",
            recognized_fields={
                "departure_airport_code": "SHA",
                "arrival_airport_code": "WUH",
                "return_departure_airport_code": "WUH",
                "return_arrival_airport_code": "SHA",
            },
        ),
    )

    assert result.rule_code == AIRFARE_ITINERARY_REQUIRED_RULE_CODE
    assert result.status is ValidationStatus.PASSED
    assert result.message == "航空费用已具备往返机场代码，无需补充行程单"


@pytest.mark.parametrize(
    ("supporting_materials", "supporting_material_recognitions", "expected_status"),
    [
        (
            [make_material("order-1", material_type=MaterialType.ORDER_SCREENSHOT, content_type="image/png")],
            {},
            ValidationStatus.PENDING,
        ),
        (
            [],
            {},
            ValidationStatus.FAILED,
        ),
        (
            [],
            {
                "material-invoice": make_recognition(
                    "material-invoice",
                    recognized_fields={
                        "departure_airport_code": "SHA",
                        "arrival_airport_code": "WUH",
                        "return_departure_airport_code": "WUH",
                        "return_arrival_airport_code": "SHA",
                    },
                )
            },
            ValidationStatus.PASSED,
        ),
        (
            [make_material("itinerary-1", material_type=MaterialType.ITINERARY)],
            {"itinerary-1": make_recognition("itinerary-1", recognized_fields={"cabin_class": "经济舱"})},
            ValidationStatus.PASSED,
        ),
    ],
)
def test_airfare_cabin_rule_covers_passed_failed_pending_paths(
    supporting_materials: list[MaterialRecord],
    supporting_material_recognitions: dict[str, RecognitionTaskRecord],
    expected_status: ValidationStatus,
):
    result = validate_airfare_cabin_requirement(
        make_invoice(expense_type=ExpenseType.AIRFARE),
        recognition_task=supporting_material_recognitions.get("material-invoice"),
        supporting_materials=supporting_materials,
        supporting_material_recognitions=supporting_material_recognitions,
    )

    assert result.rule_code == AIRFARE_CABIN_PROOF_RULE_CODE
    assert result.status is expected_status


@pytest.mark.parametrize(
    ("recognition_task", "supporting_material_recognitions", "expected_status"),
    [
        (
            make_recognition("material-invoice", recognized_fields={"transport_mode": "rideshare"}),
            {},
            ValidationStatus.FAILED,
        ),
        (
            make_recognition(
                "material-invoice",
                recognized_fields={
                    "transport_mode": "rideshare",
                    "pickup_location": "嘉定校区",
                    "dropoff_location": "虹桥火车站",
                },
            ),
            {},
            ValidationStatus.PASSED,
        ),
        (
            make_recognition("material-invoice", recognized_fields={"seller_name": "滴滴出行"}),
            {},
            ValidationStatus.PENDING,
        ),
    ],
)
def test_local_transport_rideshare_trip_rule_covers_passed_failed_pending_paths(
    recognition_task: RecognitionTaskRecord,
    supporting_material_recognitions: dict[str, RecognitionTaskRecord],
    expected_status: ValidationStatus,
):
    result = validate_local_transport_rideshare_trip_requirement(
        make_invoice(expense_type=ExpenseType.LOCAL_TRANSPORT),
        recognition_task=recognition_task,
        supporting_materials=[],
        supporting_material_recognitions=supporting_material_recognitions,
    )

    assert result.rule_code == LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE
    assert result.status is expected_status


def test_local_transport_invoice_is_treated_as_rideshare_electronic_ticket():
    result = validate_local_transport_rideshare_trip_requirement(
        make_invoice(expense_type=ExpenseType.LOCAL_TRANSPORT),
        recognition_task=make_recognition(
            "material-invoice",
            recognized_fields={
                "material_type": "invoice",
                "expense_type": "local_transport",
            },
        ),
        supporting_materials=[],
        supporting_material_recognitions={},
    )

    assert result.rule_code == LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE
    assert result.status is ValidationStatus.FAILED
    assert result.message == "网约车费用缺少行程信息"
    assert result.evidence["rideshare_detections"][-1]["field_name"] == (
        "local_transport_electronic_invoice_policy"
    )


def test_local_transport_electronic_invoice_passes_when_trip_record_is_linked():
    itinerary = make_material("itinerary-1", material_type=MaterialType.ITINERARY)

    result = validate_local_transport_rideshare_trip_requirement(
        make_invoice(expense_type=ExpenseType.LOCAL_TRANSPORT),
        recognition_task=make_recognition(
            "material-invoice",
            recognized_fields={
                "material_type": "invoice",
                "expense_type": "local_transport",
            },
        ),
        supporting_materials=[itinerary],
        supporting_material_recognitions={
            "itinerary-1": make_recognition(
                "itinerary-1",
                recognized_fields={
                    "transport_mode": "taxi",
                    "trip_route": "虹桥站 至 同济大学嘉定校区",
                },
            )
        },
    )

    assert result.rule_code == LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE
    assert result.status is ValidationStatus.PASSED


@pytest.mark.parametrize(
    ("transaction_time", "expected_status"),
    [
        (datetime(2026, 5, 2, 8, 0, tzinfo=timezone.utc), ValidationStatus.NOT_APPLICABLE),
        (datetime(2026, 5, 10, 8, 0, tzinfo=timezone.utc), ValidationStatus.NOT_APPLICABLE),
        (None, ValidationStatus.NOT_APPLICABLE),
    ],
)
def test_competition_time_range_rule_no_longer_limits_invoice_transaction_time(
    transaction_time: datetime | None,
    expected_status: ValidationStatus,
):
    result = validate_competition_time_range(
        make_invoice(expense_type=ExpenseType.HOTEL, transaction_time=transaction_time),
        make_task(),
    )

    assert result.rule_code == COMPETITION_TIME_RANGE_RULE_CODE
    assert result.status is expected_status
    assert result.message == "当前不限制发票交易产生时间"


@pytest.mark.parametrize(
    ("recognition_task", "expected_status"),
    [
        (
            make_recognition(
                "material-invoice",
                recognized_fields={
                    "departure_location": "Nanjing South Railway Station",
                    "arrival_location": "Shanghai Hongqiao Railway Station",
                },
            ),
            ValidationStatus.PASSED,
        ),
        (
            make_recognition(
                "material-invoice",
                recognized_fields={
                    "departure_location": "Nanjing South Railway Station",
                    "arrival_location": "Suzhou Railway Station",
                },
            ),
            ValidationStatus.FAILED,
        ),
        (
            make_recognition("material-invoice", recognized_fields={"seller_name": "铁路服务商"}),
            ValidationStatus.PENDING,
        ),
    ],
)
def test_competition_location_range_rule_covers_passed_failed_pending_paths(
    recognition_task: RecognitionTaskRecord,
    expected_status: ValidationStatus,
):
    result = validate_competition_location_range(
        make_invoice(expense_type=ExpenseType.RAILWAY),
        make_task(),
        recognition_task,
        supporting_materials=[],
        supporting_material_recognitions={},
    )

    assert result.rule_code == COMPETITION_LOCATION_RANGE_RULE_CODE
    assert result.status is expected_status
