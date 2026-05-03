import csv
from io import BytesIO, StringIO

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task as create_admin_task,
    register_and_get_token,
    update_task_row,
    valid_invoice_payload,
    valid_task_payload,
)


def make_client(tmp_path):
    runtime_config = load_runtime_config(
        environment="test",
        database_url=f"sqlite:///{tmp_path}/test.db",
        material_storage_dir=tmp_path / "material-storage",
        cors_allowed_origins="http://127.0.0.1:5173",
        public_api_base_url="http://127.0.0.1:8000/api",
        api_host="127.0.0.1",
        api_port=8000,
        async_job_mode="worker",
    )
    return TestClient(
        create_app(
            runtime_config=runtime_config,
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_task(client: TestClient) -> str:
    return create_admin_task(client)["id"]


def create_task_with_overrides(client: TestClient, **overrides) -> str:
    return create_admin_task(client, payload=valid_task_payload() | overrides)["id"]


def create_export_job(
    client: TestClient,
    task_id: str,
    *,
    kind: str = "reimbursement_summary",
    format: str = "xlsx",
    parameters: dict | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    response = client.post(
        f"/api/tasks/{task_id}/exports",
        headers=headers or admin_auth_headers(client),
        json={
            "kind": kind,
            "format": format,
            "parameters": parameters or {},
        },
    )
    assert response.status_code == 201
    return response.json()


def member_auth_headers(
    client: TestClient,
    *,
    username: str,
    actor_id: str,
) -> dict[str, str]:
    return auth_headers(
        register_and_get_token(
            client,
            username=username,
            role="member",
            actor_id=actor_id,
            member_code=actor_id,
        )
    )


def upload_invoice_material(
    client: TestClient,
    task_id: str,
    *,
    submitter_id: str,
    filename: str,
    content: bytes | None = None,
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": submitter_id,
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": (filename, content if content is not None else filename.encode(), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def upload_supporting_material(
    client: TestClient,
    task_id: str,
    *,
    submitter_id: str,
    material_type: str,
    filename: str,
    content_type: str = "application/pdf",
    content: bytes | None = None,
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": submitter_id,
            "channel": "web",
            "material_type": material_type,
        },
        files={
            "files": (
                filename,
                content if content is not None else filename.encode(),
                content_type,
            )
        },
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def create_invoice_with_splits(
    client: TestClient,
    task_id: str,
    *,
    submitter_id: str,
    filename: str,
    material_content: bytes | None = None,
    invoice_overrides: dict | None = None,
    split_items: list[dict] | None = None,
) -> str:
    invoice_id, _ = create_invoice_with_splits_and_material(
        client,
        task_id,
        submitter_id=submitter_id,
        filename=filename,
        material_content=material_content,
        invoice_overrides=invoice_overrides,
        split_items=split_items,
    )
    return invoice_id


def create_invoice_with_splits_and_material(
    client: TestClient,
    task_id: str,
    *,
    submitter_id: str,
    filename: str,
    material_content: bytes | None = None,
    invoice_overrides: dict | None = None,
    split_items: list[dict] | None = None,
) -> tuple[str, str]:
    material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id=submitter_id,
        filename=filename,
        content=material_content,
    )
    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=(valid_invoice_payload() | {"actor_id": submitter_id} | (invoice_overrides or {})),
    )
    assert response.status_code == 201
    invoice_id = response.json()["invoice"]["id"]
    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": submitter_id,
            "items": split_items or [{"member_id": submitter_id, "amount_cents": 12345}],
        },
    )
    assert response.status_code == 200
    return invoice_id, material_id


def confirm_split(
    client: TestClient,
    *,
    split_id: str,
    member_id: str,
) -> None:
    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={"actor_id": member_id, "member_id": member_id, "status": "confirmed"},
    )
    assert response.status_code == 200


def build_pdf_bytes(*, encrypted: bool = False, width: int = 200, height: int = 200) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    if encrypted:
        writer.encrypt("secret")
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_png_bytes() -> bytes:
    image = Image.new("RGB", (120, 80), (64, 128, 192))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_task_administrator_can_get_export_capabilities_when_task_is_ready(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["administrator_id"] == "admin-1"
    assert body["current_task_status"] == "ready_to_export"
    assert body["export_allowed"] is True
    assert body["blocking_reasons"] == []


def test_secondary_task_administrator_can_get_export_capabilities(tmp_path):
    client = make_client(tmp_path)
    secondary_admin_token = register_and_get_token(
        client,
        username="admin2",
        role="admin",
        actor_id="admin-2",
        member_code=None,
    )
    task_id = create_task_with_overrides(client, administrator_ids=["admin-1", "admin-2"])
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        params={"actor_id": "admin-2"},
        headers=auth_headers(secondary_admin_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["administrator_id"] == "admin-2"
    assert body["execution_mode"] == "async_worker"
    assert body["note"] == "当前导出会通过后台任务生成，并在成功后保留可下载产物。"
    supported_by_kind = {item["kind"]: item for item in body["supported_exports"]}
    assert set(supported_by_kind) == {
        "reimbursement_summary",
        "member_details",
        "invoice_details",
        "missing_materials",
        "finance_draft",
        "merged_pdf",
        "reimbursement_package",
        "original_materials_archive",
    }
    assert supported_by_kind["reimbursement_summary"]["formats"] == ["xlsx", "csv"]
    assert supported_by_kind["reimbursement_summary"]["implemented"] is True
    assert supported_by_kind["reimbursement_summary"]["implemented_formats"] == ["csv"]
    assert supported_by_kind["member_details"]["formats"] == ["xlsx", "csv"]
    assert supported_by_kind["member_details"]["implemented"] is True
    assert supported_by_kind["member_details"]["implemented_formats"] == ["csv"]
    assert supported_by_kind["invoice_details"]["formats"] == ["xlsx", "csv"]
    assert supported_by_kind["invoice_details"]["implemented"] is True
    assert supported_by_kind["invoice_details"]["implemented_formats"] == ["csv"]
    assert supported_by_kind["missing_materials"]["formats"] == ["xlsx", "csv"]
    assert supported_by_kind["missing_materials"]["implemented"] is True
    assert supported_by_kind["missing_materials"]["implemented_formats"] == ["csv"]
    assert supported_by_kind["finance_draft"]["formats"] == ["xlsx", "json"]
    assert supported_by_kind["finance_draft"]["implemented"] is True
    assert supported_by_kind["finance_draft"]["implemented_formats"] == ["json"]
    assert supported_by_kind["merged_pdf"]["formats"] == ["pdf"]
    assert supported_by_kind["merged_pdf"]["implemented"] is True
    assert supported_by_kind["merged_pdf"]["implemented_formats"] == ["pdf"]
    assert supported_by_kind["reimbursement_package"]["formats"] == ["zip"]
    assert supported_by_kind["reimbursement_package"]["implemented"] is True
    assert supported_by_kind["reimbursement_package"]["implemented_formats"] == ["zip"]
    assert supported_by_kind["original_materials_archive"]["formats"] == ["zip"]
    assert supported_by_kind["original_materials_archive"]["implemented"] is True
    assert supported_by_kind["original_materials_archive"]["implemented_formats"] == ["zip"]


def test_task_administrator_can_export_reimbursement_summary_csv(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="railway-a.pdf",
        split_items=[
            {"member_id": "2250001", "amount_cents": 6000},
            {"member_id": "2250002", "amount_cents": 6345},
        ],
    )
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250003",
        filename="registration.pdf",
        invoice_overrides={
            "invoice_number": "INV-002",
            "amount_cents": 20000,
            "expense_type": "registration",
            "seller_name": "比赛平台",
        },
        split_items=[{"member_id": "2250003", "amount_cents": 20000}],
    )
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="railway-b.pdf",
        invoice_overrides={
            "invoice_number": "INV-003",
            "amount_cents": 1555,
        },
        split_items=[{"member_id": "2250001", "amount_cents": 1555}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/reimbursement-summary",
        params={"actor_id": "admin-1", "format": "csv"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{task_id}-reimbursement-summary.csv"'
    )

    rows = list(csv.DictReader(StringIO(response.text)))
    assert rows == [
        {
            "expense_type": "registration",
            "total_amount_cents": "20000",
            "2250001": "0",
            "2250002": "0",
            "2250003": "20000",
        },
        {
            "expense_type": "railway",
            "total_amount_cents": "13900",
            "2250001": "7555",
            "2250002": "6345",
            "2250003": "0",
        },
        {
            "expense_type": "hotel",
            "total_amount_cents": "0",
            "2250001": "0",
            "2250002": "0",
            "2250003": "0",
        },
        {
            "expense_type": "grand_total",
            "total_amount_cents": "33900",
            "2250001": "7555",
            "2250002": "6345",
            "2250003": "20000",
        },
    ]


def test_task_administrator_can_export_member_details_csv_with_current_split_versions(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    first_invoice_id = create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="railway-a.pdf",
        split_items=[
            {"member_id": "2250001", "amount_cents": 6000, "note": "initial-self"},
            {"member_id": "2250002", "amount_cents": 6345, "note": "initial-shared"},
        ],
    )
    initial_splits = client.get(f"/api/invoices/{first_invoice_id}/splits")
    assert initial_splits.status_code == 200
    split_ids = {item["member_id"]: item["id"] for item in initial_splits.json()["items"]}
    confirm_split(client, split_id=split_ids["2250001"], member_id="2250001")
    confirm_split(client, split_id=split_ids["2250002"], member_id="2250002")

    replace_response = client.put(
        f"/api/invoices/{first_invoice_id}/splits",
        json={
            "actor_id": "admin-1",
            "items": [
                {"member_id": "2250001", "amount_cents": 6100, "note": "final-self"},
                {"member_id": "2250002", "amount_cents": 6245, "note": "final-shared"},
            ],
        },
    )
    assert replace_response.status_code == 200

    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250003",
        filename="registration.pdf",
        invoice_overrides={
            "invoice_number": "INV-002",
            "amount_cents": 20000,
            "expense_type": "registration",
            "seller_name": "比赛平台",
        },
        split_items=[
            {"member_id": "2250002", "amount_cents": 10000},
            {"member_id": "2250003", "amount_cents": 10000},
        ],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/member-details",
        params={"actor_id": "admin-1", "format": "csv"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{task_id}-member-details.csv"'
    )

    rows = list(csv.DictReader(StringIO(response.text)))
    assert rows == [
        {
            "member_id": "2250001",
            "expense_type": "railway",
            "invoice_number": "INV-001",
            "invoice_amount_cents": "12345",
            "split_amount_cents": "6100",
            "split_version": "3",
            "confirmation_status": "pending",
            "split_note": "final-self",
        },
        {
            "member_id": "2250002",
            "expense_type": "railway",
            "invoice_number": "INV-001",
            "invoice_amount_cents": "12345",
            "split_amount_cents": "6245",
            "split_version": "2",
            "confirmation_status": "pending",
            "split_note": "final-shared",
        },
        {
            "member_id": "2250002",
            "expense_type": "registration",
            "invoice_number": "INV-002",
            "invoice_amount_cents": "20000",
            "split_amount_cents": "10000",
            "split_version": "1",
            "confirmation_status": "",
            "split_note": "",
        },
        {
            "member_id": "2250003",
            "expense_type": "registration",
            "invoice_number": "INV-002",
            "invoice_amount_cents": "20000",
            "split_amount_cents": "10000",
            "split_version": "2",
            "confirmation_status": "confirmed",
            "split_note": "",
        },
        {
            "member_id": "grand_total",
            "expense_type": "",
            "invoice_number": "",
            "invoice_amount_cents": "",
            "split_amount_cents": "32345",
            "split_version": "",
            "confirmation_status": "",
            "split_note": "",
        },
    ]


def test_task_administrator_can_export_invoice_details_csv_with_validation_summary(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="railway-a.pdf",
    )
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250002",
        filename="registration.pdf",
        invoice_overrides={
            "invoice_number": "INV-001",
            "amount_cents": 20000,
            "expense_type": "registration",
            "seller_name": "比赛平台",
        },
        split_items=[{"member_id": "2250002", "amount_cents": 20000}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/invoice-details",
        params={"actor_id": "admin-1", "format": "csv"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{task_id}-invoice-details.csv"'
    )

    rows = list(csv.DictReader(StringIO(response.text)))
    assert len(rows) == 2

    assert rows[0] == {
        "invoice_number": "INV-001",
        "amount_cents": "12345",
        "expense_type": "railway",
        "submitter_id": "2250001",
        "validation_status": "passed",
        "failed_rule_codes": "",
        "pending_rule_codes": "",
        "abnormal_validation_messages": "",
    }
    assert rows[1] == {
        "invoice_number": "INV-001",
        "amount_cents": "20000",
        "expense_type": "registration",
        "submitter_id": "2250002",
        "validation_status": "failed",
        "failed_rule_codes": "invoice_competition_notice_required;invoice_number_unique",
        "pending_rule_codes": "",
        "abnormal_validation_messages": rows[1]["abnormal_validation_messages"],
    }
    assert "发票号码与" in rows[1]["abnormal_validation_messages"]
    assert "重复" in rows[1]["abnormal_validation_messages"]
    assert "缺少比赛通知" in rows[1]["abnormal_validation_messages"]


def test_task_administrator_can_export_missing_materials_csv(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task_with_overrides(
        client,
        fee_categories=["registration", "railway", "airfare"],
    )
    update_task_row(tmp_path, task_id, status="open")

    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="payment-required.pdf",
        invoice_overrides={
            "invoice_number": "PAY-001",
            "amount_cents": 150000,
            "expense_type": "railway",
        },
        split_items=[{"member_id": "2250001", "amount_cents": 150000}],
    )
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250002",
        filename="registration.pdf",
        invoice_overrides={
            "invoice_number": "REG-001",
            "amount_cents": 20000,
            "expense_type": "registration",
            "seller_name": "比赛平台",
        },
        split_items=[{"member_id": "2250002", "amount_cents": 20000}],
    )
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250003",
        filename="airfare.pdf",
        invoice_overrides={
            "invoice_number": "AIR-001",
            "amount_cents": 80000,
            "expense_type": "airfare",
            "seller_name": "航空公司",
        },
        split_items=[{"member_id": "2250003", "amount_cents": 80000}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/missing-materials",
        params={"actor_id": "admin-1", "format": "csv"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{task_id}-missing-materials.csv"'
    )

    rows = list(csv.DictReader(StringIO(response.text)))
    assert rows == [
        {
            "member_id": "2250001",
            "expense_type": "railway",
            "invoice_number": "PAY-001",
            "required_material_type": "payment_record",
            "source_rule_code": "invoice_payment_record_required",
            "message": "发票金额达到阈值，缺少支付记录",
        },
        {
            "member_id": "2250002",
            "expense_type": "registration",
            "invoice_number": "REG-001",
            "required_material_type": "competition_notice",
            "source_rule_code": "invoice_competition_notice_required",
            "message": "参赛费缺少比赛通知",
        },
        {
            "member_id": "2250003",
            "expense_type": "airfare",
            "invoice_number": "AIR-001",
            "required_material_type": "itinerary",
            "source_rule_code": "invoice_airfare_itinerary_required",
            "message": "航空费用缺少行程单",
        },
    ]


def test_task_administrator_can_export_empty_missing_materials_csv(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    invoice_id = create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="registration.pdf",
        invoice_overrides={
            "invoice_number": "REG-001",
            "amount_cents": 20000,
            "expense_type": "registration",
            "seller_name": "比赛平台",
        },
        split_items=[{"member_id": "2250001", "amount_cents": 20000}],
    )
    competition_notice_material_id = upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="competition_notice",
        filename="notice.pdf",
    )
    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{competition_notice_material_id}",
        headers=admin_auth_headers(client),
    )
    assert attach_response.status_code == 200
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/missing-materials",
        params={"actor_id": "admin-1", "format": "csv"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert (
        response.text.strip()
        == "member_id,expense_type,invoice_number,required_material_type,source_rule_code,message"
    )
    rows = list(csv.DictReader(StringIO(response.text)))
    assert rows == []


def test_task_administrator_can_export_finance_draft_json(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="railway-a.pdf",
        split_items=[
            {"member_id": "2250001", "amount_cents": 6000, "note": "self"},
            {"member_id": "2250002", "amount_cents": 6345, "note": "shared"},
        ],
    )
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250003",
        filename="hotel.pdf",
        invoice_overrides={
            "invoice_number": "INV-002",
            "amount_cents": 20000,
            "expense_type": "hotel",
            "seller_name": "酒店商户",
        },
        split_items=[{"member_id": "2250003", "amount_cents": 20000}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/finance-draft",
        params={"actor_id": "admin-1", "format": "json"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{task_id}-finance-draft.json"'
    )

    body = response.json()
    assert body["task_id"] == task_id
    assert body["administrator_id"] == "admin-1"
    assert body["format"] == "json"
    assert body["competition_name"] == "ICPC Asia Regional"
    assert body["competition_location"] == "Shanghai"
    assert body["project_info"] == ""
    assert body["reimburser_info"] == ""
    assert body["invoice_title"] == "同济大学"
    assert body["tax_number"] == "12100000425006117D"
    assert body["total_amount_cents"] == 32345
    assert body["invoice_count"] == 2
    assert body["expense_totals_cents"] == {
        "registration": 0,
        "railway": 12345,
        "hotel": 20000,
    }
    assert body["member_totals_cents"] == {
        "2250001": 6000,
        "2250002": 6345,
        "2250003": 20000,
    }
    assert body["invoice_rows"] == [
        {
            "invoice_number": "INV-002",
            "expense_type": "hotel",
            "amount_cents": 20000,
            "buyer_name": "同济大学",
            "tax_number": "12100000425006117D",
            "seller_name": "酒店商户",
            "issue_date": "2026-11-04",
            "transaction_time": "2026-11-01T08:00:00",
            "submitter_id": "2250003",
            "validation_status": "passed",
            "failed_rule_codes": [],
            "pending_rule_codes": [],
            "split_items": [
                {
                    "member_id": "2250003",
                    "amount_cents": 20000,
                    "split_version": 1,
                    "split_note": None,
                }
            ],
        },
        {
            "invoice_number": "INV-001",
            "expense_type": "railway",
            "amount_cents": 12345,
            "buyer_name": "同济大学",
            "tax_number": "12100000425006117D",
            "seller_name": "铁路服务商",
            "issue_date": "2026-11-04",
            "transaction_time": "2026-11-01T08:00:00",
            "submitter_id": "2250001",
            "validation_status": "passed",
            "failed_rule_codes": [],
            "pending_rule_codes": [],
            "split_items": [
                {
                    "member_id": "2250001",
                    "amount_cents": 6000,
                    "split_version": 2,
                    "split_note": "self",
                },
                {
                    "member_id": "2250002",
                    "amount_cents": 6345,
                    "split_version": 1,
                    "split_note": "shared",
                },
            ],
        },
    ]
    assert "storage_key" not in response.text
    assert str(tmp_path) not in response.text


def test_task_administrator_can_preview_merged_pdf_plan_in_default_order(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    invoice_material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice.pdf",
        content=build_pdf_bytes(),
    )
    supporting_material_id = upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="competition_notice",
        filename="notice.pdf",
        content=build_pdf_bytes(),
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/merged-pdf",
        params={"actor_id": "admin-1", "format": "pdf"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["task_id"] == task_id
    assert body["format"] == "pdf"
    assert body["filename"] == f"{task_id}-merged-printing.pdf"
    assert [item["kind"] for item in body["ordered_items"]] == [
        "invoice_material",
        "supporting_material",
    ]
    assert all(item["status"] == "ready" for item in body["ordered_items"])
    assert body["ordered_items"][0]["material_id"] == invoice_material_id
    assert body["ordered_items"][0]["original_filename"] == "invoice.pdf"
    assert body["ordered_items"][1]["material_id"] == supporting_material_id
    assert body["ordered_items"][1]["original_filename"] == "notice.pdf"


def test_merged_pdf_preview_accepts_supported_image_material(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    material_id = upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="order_screenshot",
        filename="ticket.png",
        content_type="image/png",
        content=build_png_bytes(),
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/merged-pdf",
        params={"actor_id": "admin-1", "format": "pdf"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["ordered_items"] == [
        {
            "sequence": 1,
            "kind": "supporting_material",
            "status": "ready",
            "label": "ticket.png",
            "note": None,
            "material_id": material_id,
            "material_type": "order_screenshot",
            "original_filename": "ticket.png",
        }
    ]


def test_merged_pdf_preview_marks_paper_invoice_placeholder_without_blocking(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task_with_overrides(client, fee_categories=["registration", "railway"])
    update_task_row(tmp_path, task_id, status="open")
    member_headers = member_auth_headers(
        client,
        username="paper-member-export-preview",
        actor_id="2250001",
    )

    create_response = client.post(
        f"/api/tasks/{task_id}/paper-invoices",
        json=valid_invoice_payload() | {
            "invoice_number": "PAPER-IGNORED-001",
            "expense_type": "registration",
            "amount_cents": 8800,
        },
        headers=member_headers,
    )
    assert create_response.status_code == 201
    paper_invoice = create_response.json()["invoice"]

    invoice_material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice.pdf",
        content=build_pdf_bytes(),
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/merged-pdf",
        params={"actor_id": "admin-1", "format": "pdf"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["ordered_items"] == [
        {
            "sequence": 1,
            "kind": "invoice_material",
            "status": "placeholder",
            "label": f"paper-invoice-{paper_invoice['invoice_number']}.txt",
            "note": (
                f"纸质发票 {paper_invoice['invoice_number']} 仅记录线下收票，不会出现在 "
                "merged-printing.pdf 中。"
            ),
            "material_id": paper_invoice["material_id"],
            "material_type": "invoice",
            "original_filename": f"paper-invoice-{paper_invoice['invoice_number']}.txt",
        },
        {
            "sequence": 2,
            "kind": "invoice_material",
            "status": "ready",
            "label": "invoice.pdf",
            "note": None,
            "material_id": invoice_material_id,
            "material_type": "invoice",
            "original_filename": "invoice.pdf",
        },
    ]


def test_merged_pdf_preview_places_supporting_materials_after_related_invoice_block(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    invoice_a_id, invoice_a_material_id = create_invoice_with_splits_and_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-a.pdf",
        material_content=build_pdf_bytes(width=101, height=101),
        invoice_overrides={"invoice_number": "INV-A"},
    )
    invoice_b_id, invoice_b_material_id = create_invoice_with_splits_and_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-b.pdf",
        material_content=build_pdf_bytes(width=202, height=202),
        invoice_overrides={"invoice_number": "INV-B"},
    )
    invoice_c_id, invoice_c_material_id = create_invoice_with_splits_and_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-c.pdf",
        material_content=build_pdf_bytes(width=303, height=303),
        invoice_overrides={"invoice_number": "INV-C"},
    )
    exclusive_attachment_material_id = upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="attachment-a.pdf",
        content=build_pdf_bytes(width=111, height=111),
    )
    shared_attachment_material_id = upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="competition_notice",
        filename="attachment-shared.pdf",
        content=build_pdf_bytes(width=222, height=222),
    )
    for invoice_id, material_id in (
        (invoice_a_id, exclusive_attachment_material_id),
        (invoice_a_id, shared_attachment_material_id),
        (invoice_c_id, shared_attachment_material_id),
    ):
        attach_response = client.put(
            f"/api/invoices/{invoice_id}/supporting-materials/{material_id}",
            headers=admin_auth_headers(client),
        )
        assert attach_response.status_code == 200

    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/merged-pdf",
        params={"actor_id": "admin-1", "format": "pdf"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert [item["material_id"] for item in response.json()["ordered_items"]] == [
        invoice_a_material_id,
        exclusive_attachment_material_id,
        invoice_c_material_id,
        shared_attachment_material_id,
        invoice_b_material_id,
    ]
    assert [item["original_filename"] for item in response.json()["ordered_items"]] == [
        "invoice-a.pdf",
        "attachment-a.pdf",
        "invoice-c.pdf",
        "attachment-shared.pdf",
        "invoice-b.pdf",
    ]


def test_merged_pdf_preview_reports_encrypted_material_id(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="encrypted.pdf",
        content=build_pdf_bytes(encrypted=True),
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/merged-pdf",
        params={"actor_id": "admin-1", "format": "pdf"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == f"merged pdf source material {material_id} is encrypted"


def test_merged_pdf_preview_reports_unreadable_material_id(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="broken.pdf",
        content=b"%PDF-1.4 broken",
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/merged-pdf",
        params={"actor_id": "admin-1", "format": "pdf"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith(
        f"merged pdf source material {material_id} is unreadable:"
    )


def test_finance_draft_xlsx_is_not_implemented_yet(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/finance-draft",
        params={"actor_id": "admin-1", "format": "xlsx"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "export format xlsx is not implemented yet for finance_draft"
    )


def test_export_capabilities_report_blocking_reason_before_final_confirmation(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="reviewing")

    response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["export_allowed"] is False
    assert response.json()["blocking_reasons"] == [
        "当前任务还未进入“可导出”或“已完成”阶段，暂时不能生成正式导出材料。"
    ]


def test_export_routes_require_bearer_identity(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    capabilities_response = client.get(f"/api/tasks/{task_id}/exports/capabilities")
    assert capabilities_response.status_code == 401
    assert capabilities_response.json()["detail"] == "invalid or missing bearer token"

    create_response = client.post(
        f"/api/tasks/{task_id}/exports",
        json={
            "kind": "reimbursement_summary",
            "format": "csv",
            "parameters": {},
        },
    )
    assert create_response.status_code == 401
    assert create_response.json()["detail"] == "invalid or missing bearer token"

    list_response = client.get(f"/api/tasks/{task_id}/exports")
    assert list_response.status_code == 401
    assert list_response.json()["detail"] == "invalid or missing bearer token"


def test_non_administrator_cannot_get_export_capabilities(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)

    response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        params={"actor_id": "2250001"},
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to manage exports for this task"


def test_non_administrator_cannot_export_reimbursement_summary(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/reimbursement-summary",
        params={"actor_id": "2250001", "format": "csv"},
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to manage exports for this task"


def test_create_and_list_export_jobs_persist_requested_parameters(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    created = create_export_job(
        client,
        task_id,
        parameters={"include_member_breakdown": True, "locale": "zh-CN"},
    )

    assert created["task_id"] == task_id
    assert created["requested_by"] == "admin-1"
    assert created["kind"] == "reimbursement_summary"
    assert created["format"] == "xlsx"
    assert created["status"] == "pending"
    assert created["parameters"] == {
        "include_member_breakdown": True,
        "locale": "zh-CN",
    }
    assert created["task_status_at_request"] == "ready_to_export"
    assert len(created["task_data_version"]) == 64
    assert created["is_latest_for_task"] is True
    assert created["retry_count"] == 0
    assert created["artifact"] is None
    assert created["failure_reason"] is None
    assert created["created_at"]
    assert created["updated_at"]
    assert created["started_at"] is None
    assert created["finished_at"] is None

    listed = client.get(
        f"/api/tasks/{task_id}/exports",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert listed.status_code == 200
    assert listed.json() == [created]


def test_export_jobs_are_marked_stale_after_task_data_changes(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    first_job = create_export_job(client, task_id)

    update_task_row(
        tmp_path,
        task_id,
        project_info="ACM competition project (revised)",
    )

    second_job = create_export_job(client, task_id)

    assert first_job["task_data_version"] != second_job["task_data_version"]
    assert second_job["is_latest_for_task"] is True

    listed = client.get(
        f"/api/tasks/{task_id}/exports",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 2
    assert body[0]["id"] == first_job["id"]
    assert body[0]["task_status_at_request"] == "ready_to_export"
    assert body[0]["is_latest_for_task"] is False
    assert body[0]["retry_count"] == 0
    assert body[1]["id"] == second_job["id"]
    assert body[1]["task_data_version"] == second_job["task_data_version"]
    assert body[1]["is_latest_for_task"] is True
    assert body[1]["retry_count"] == 0


def test_export_job_retry_count_increments_for_same_request_signature(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    first_job = create_export_job(
        client,
        task_id,
        format="csv",
        parameters={"locale": "zh-CN"},
    )
    second_job = create_export_job(
        client,
        task_id,
        format="csv",
        parameters={"locale": "zh-CN"},
    )

    listed = client.get(
        f"/api/tasks/{task_id}/exports",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert listed.status_code == 200
    body = listed.json()
    assert [item["id"] for item in body] == [first_job["id"], second_job["id"]]
    assert body[0]["retry_count"] == 0
    assert body[1]["retry_count"] == 1


def test_export_job_status_transitions_cover_running_succeeded_and_failed(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    first_job = create_export_job(client, task_id)

    running = client.patch(
        f"/api/tasks/exports/{first_job['id']}/status",
        headers=admin_auth_headers(client),
        json={"target_status": "running"},
    )
    assert running.status_code == 200
    assert running.json()["status"] == "running"
    assert running.json()["is_latest_for_task"] is True
    assert running.json()["retry_count"] == 0
    assert running.json()["artifact"] is None
    assert running.json()["started_at"] is not None
    assert running.json()["finished_at"] is None

    succeeded = client.patch(
        f"/api/tasks/exports/{first_job['id']}/status",
        headers=admin_auth_headers(client),
        json={"target_status": "succeeded"},
    )
    assert succeeded.status_code == 200
    assert succeeded.json()["status"] == "succeeded"
    assert succeeded.json()["is_latest_for_task"] is True
    assert succeeded.json()["retry_count"] == 0
    assert succeeded.json()["artifact"] is None
    assert succeeded.json()["started_at"] is not None
    assert succeeded.json()["finished_at"] is not None
    assert succeeded.json()["failure_reason"] is None

    second_job = create_export_job(
        client,
        task_id,
        kind="merged_pdf",
        format="pdf",
    )
    failed = client.patch(
        f"/api/tasks/exports/{second_job['id']}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "failed",
            "failure_reason": "failed to read encrypted material PDF",
        },
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["is_latest_for_task"] is True
    assert failed.json()["retry_count"] == 0
    assert failed.json()["artifact"] is None
    assert failed.json()["failure_reason"] == "failed to read encrypted material PDF"
    assert failed.json()["finished_at"] is not None


def test_create_export_job_requires_ready_to_export_or_completed_task(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="reviewing")

    response = client.post(
        f"/api/tasks/{task_id}/exports",
        headers=admin_auth_headers(client),
        json={
            "kind": "reimbursement_summary",
            "format": "xlsx",
            "parameters": {},
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "task is not ready for export: 当前任务还未进入“可导出”或“已完成”阶段，暂时不能生成正式导出材料。"
    )


def test_non_administrator_cannot_manage_export_jobs(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(client, task_id)

    create_response = client.post(
        f"/api/tasks/{task_id}/exports",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
        json={
            "kind": "reimbursement_summary",
            "format": "xlsx",
            "parameters": {},
        },
    )
    assert create_response.status_code == 403
    assert create_response.json()["detail"] == (
        "actor is not allowed to manage exports for this task"
    )

    list_response = client.get(
        f"/api/tasks/{task_id}/exports",
        params={"actor_id": "2250001"},
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )
    assert list_response.status_code == 403
    assert list_response.json()["detail"] == (
        "actor is not allowed to manage exports for this task"
    )

    update_response = client.patch(
        f"/api/tasks/exports/{export_job['id']}/status",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
        json={"target_status": "running"},
    )
    assert update_response.status_code == 403
    assert update_response.json()["detail"] == (
        "actor is not allowed to manage exports for this task"
    )
