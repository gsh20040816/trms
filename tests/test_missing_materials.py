from datetime import datetime, timezone

from trms_backend.domain.invoice_validation import (
    AIRFARE_ITINERARY_REQUIRED_RULE_CODE,
    LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
    validate_competition_notice_requirement,
    validate_airfare_itinerary_requirement,
    validate_payment_record_requirement,
)
from trms_backend.domain.invoices import (
    ExpenseType,
    InvoiceRecord,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from trms_backend.domain.materials import MaterialRecord, MaterialStatus, MaterialType, SubmissionChannel
from trms_backend.domain.missing_materials import aggregate_task_missing_materials


def make_material(
    material_id: str,
    *,
    task_id: str,
    submitter_id: str,
    material_type: MaterialType = MaterialType.INVOICE,
    created_at: datetime,
) -> MaterialRecord:
    return MaterialRecord(
        id=material_id,
        status=MaterialStatus.ASSIGNED,
        task_id=task_id,
        submitter_id=submitter_id,
        task_id_hint=None,
        submitter_id_hint=None,
        channel=SubmissionChannel.WEB,
        material_type=material_type,
        storage_key=f"{material_id}.pdf",
        original_filename=f"{material_id}.pdf",
        content_type="application/pdf",
        size_bytes=128,
        sha256=material_id.rjust(64, "0")[:64],
        duplicate_of=None,
        claimed_by=None,
        claimed_at=None,
        created_at=created_at,
    )


def make_invoice(
    invoice_id: str,
    *,
    task_id: str,
    material_id: str,
    invoice_number: str,
    amount_cents: int,
    expense_type: ExpenseType,
    created_at: datetime,
) -> InvoiceRecord:
    return InvoiceRecord(
        id=invoice_id,
        task_id=task_id,
        material_id=material_id,
        invoice_number=invoice_number,
        issue_date=None,
        transaction_time=None,
        buyer_name="同济大学",
        tax_number="12100000425006117D",
        seller_name="供应商",
        amount_cents=amount_cents,
        expense_type=expense_type,
        created_at=created_at,
        updated_at=created_at,
    )


def test_aggregate_task_missing_materials_groups_items_by_task_and_member():
    created_at = datetime(2026, 4, 28, 4, 7, tzinfo=timezone.utc)
    task_id = "task-1"

    material_1 = make_material("material-1", task_id=task_id, submitter_id="2250001", created_at=created_at)
    material_2 = make_material(
        "material-2",
        task_id=task_id,
        submitter_id="2250002",
        created_at=created_at.replace(minute=8),
    )
    invoice_1 = make_invoice(
        "invoice-1",
        task_id=task_id,
        material_id=material_1.id,
        invoice_number="INV-001",
        amount_cents=150_000,
        expense_type=ExpenseType.REGISTRATION,
        created_at=created_at,
    )
    invoice_2 = make_invoice(
        "invoice-2",
        task_id=task_id,
        material_id=material_2.id,
        invoice_number="INV-002",
        amount_cents=50_000,
        expense_type=ExpenseType.REGISTRATION,
        created_at=created_at.replace(minute=8),
    )

    validations_by_invoice_id = {
        invoice_1.id: [
            validate_payment_record_requirement(invoice_1, []),
            validate_competition_notice_requirement(invoice_1, []),
        ],
        invoice_2.id: [
            validate_payment_record_requirement(invoice_2, []),
            validate_competition_notice_requirement(invoice_2, []),
        ],
    }

    missing_materials = aggregate_task_missing_materials(
        task_id=task_id,
        invoices=[invoice_1, invoice_2],
        materials_by_id={material_1.id: material_1, material_2.id: material_2},
        validations_by_invoice_id=validations_by_invoice_id,
    )

    assert missing_materials.task_id == task_id
    assert [(item.member_id, item.invoice_id, item.required_material_type.value) for item in missing_materials.items] == [
        ("2250001", "invoice-1", "payment_record"),
        ("2250001", "invoice-1", "competition_notice"),
        ("2250002", "invoice-2", "competition_notice"),
    ]
    assert missing_materials.items[0].message == "发票金额达到阈值，缺少支付记录"
    assert missing_materials.items[0].evidence["requires_payment_record"] is True
    assert [member.member_id for member in missing_materials.members] == ["2250001", "2250002"]
    assert [item.required_material_type.value for item in missing_materials.members[0].items] == [
        "payment_record",
        "competition_notice",
    ]
    assert [item.invoice_number for item in missing_materials.members[1].items] == ["INV-002"]


def test_aggregate_task_missing_materials_ignores_non_missing_or_unsupported_validations():
    created_at = datetime(2026, 4, 28, 4, 7, tzinfo=timezone.utc)
    task_id = "task-1"
    material = make_material("material-1", task_id=task_id, submitter_id="2250001", created_at=created_at)
    payment_record = make_material(
        "material-2",
        task_id=task_id,
        submitter_id="2250001",
        material_type=MaterialType.PAYMENT_RECORD,
        created_at=created_at.replace(minute=8),
    )
    invoice = make_invoice(
        "invoice-1",
        task_id=task_id,
        material_id=material.id,
        invoice_number="INV-001",
        amount_cents=150_000,
        expense_type=ExpenseType.RAILWAY,
        created_at=created_at,
    )
    unrelated_failed_validation = ValidationResult(
        id="validation-1",
        rule_code="invoice_title_match",
        target_type="invoice",
        target_id=invoice.id,
        severity=ValidationSeverity.BLOCKER,
        status=ValidationStatus.FAILED,
        message="发票抬头应为同济大学",
        evidence={"expected_buyer_name": "同济大学", "actual_buyer_name": "其他单位"},
        created_at=created_at.replace(minute=9),
    )

    missing_materials = aggregate_task_missing_materials(
        task_id=task_id,
        invoices=[invoice],
        materials_by_id={material.id: material, payment_record.id: payment_record},
        validations_by_invoice_id={
            invoice.id: [
                validate_payment_record_requirement(invoice, [payment_record]),
                validate_competition_notice_requirement(invoice, []),
                unrelated_failed_validation,
            ]
        },
    )

    assert missing_materials.items == []
    assert missing_materials.members == []


def test_aggregate_task_missing_materials_includes_trip_information_requirements():
    created_at = datetime(2026, 4, 28, 4, 7, tzinfo=timezone.utc)
    task_id = "task-1"
    airfare_material = make_material(
        "material-1",
        task_id=task_id,
        submitter_id="2250001",
        created_at=created_at,
    )
    rideshare_material = make_material(
        "material-2",
        task_id=task_id,
        submitter_id="2250002",
        created_at=created_at.replace(minute=8),
    )
    airfare_invoice = make_invoice(
        "invoice-1",
        task_id=task_id,
        material_id=airfare_material.id,
        invoice_number="AIR-001",
        amount_cents=180_000,
        expense_type=ExpenseType.AIRFARE,
        created_at=created_at,
    )
    rideshare_invoice = make_invoice(
        "invoice-2",
        task_id=task_id,
        material_id=rideshare_material.id,
        invoice_number="TAXI-001",
        amount_cents=3_000,
        expense_type=ExpenseType.LOCAL_TRANSPORT,
        created_at=created_at.replace(minute=8),
    )
    rideshare_missing_trip = ValidationResult(
        id="validation-1",
        rule_code=LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
        target_type="invoice",
        target_id=rideshare_invoice.id,
        severity=ValidationSeverity.BLOCKER,
        status=ValidationStatus.FAILED,
        message="网约车费用缺少行程信息",
        evidence={"trip_information_materials": []},
        created_at=created_at.replace(minute=9),
    )

    missing_materials = aggregate_task_missing_materials(
        task_id=task_id,
        invoices=[airfare_invoice, rideshare_invoice],
        materials_by_id={
            airfare_material.id: airfare_material,
            rideshare_material.id: rideshare_material,
        },
        validations_by_invoice_id={
            airfare_invoice.id: [validate_airfare_itinerary_requirement(airfare_invoice, [])],
            rideshare_invoice.id: [rideshare_missing_trip],
        },
    )

    assert [
        (item.source_rule_code, item.required_material_type.value, item.message)
        for item in missing_materials.items
    ] == [
        (AIRFARE_ITINERARY_REQUIRED_RULE_CODE, "itinerary", "航空费用缺少行程单"),
        (LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE, "itinerary", "网约车费用缺少行程信息"),
    ]
