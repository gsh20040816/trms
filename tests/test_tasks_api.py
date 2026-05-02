from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from trms_backend.domain.global_invoice_config import GlobalInvoiceConfig
from trms_backend.infrastructure.database import build_session_factory, session_scope
from trms_backend.infrastructure.models import TaskRow
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from api_error_assertions import assert_api_error


def make_client(tmp_path, global_invoice_config: GlobalInvoiceConfig | None = None):
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
            global_invoice_config=global_invoice_config,
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def register_and_get_token(
    client: TestClient,
    *,
    username: str,
    role: str,
    actor_id: str,
    member_code: str | None,
) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "correct-password",
            "role": role,
            "display_name": username,
            "actor_id": actor_id,
            "member_code": member_code,
        },
    )
    if response.status_code == 201:
        return response.json()["access_token"]

    assert response.status_code == 409
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": "correct-password",
        },
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def admin_auth_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(
        register_and_get_token(
            client,
            username="admin1",
            role="admin",
            actor_id="admin-1",
            member_code=None,
        )
    )


def create_task(
    client: TestClient,
    *,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
):
    response = client.post(
        "/api/tasks",
        json=valid_task_payload() if payload is None else payload,
        headers=admin_auth_headers(client) if headers is None else headers,
    )
    assert response.status_code == 201
    return response.json()


def update_task_row(tmp_path, task_id: str, **updates):
    session_factory = build_session_factory(f"sqlite:///{tmp_path}/test.db")
    with session_scope(session_factory) as session:
        row = session.get(TaskRow, task_id)
        assert row is not None
        for field_name, value in updates.items():
            setattr(row, field_name, value)
        session.add(row)


def valid_task_payload():
    return {
        "competition_name": "ICPC Asia Regional",
        "competition_location": "Shanghai",
        "competition_start_date": "2026-11-01",
        "competition_end_date": "2026-11-03",
        "deadline": "2026-12-01T00:00:00Z",
        "member_ids": ["2250001", "2250002", "2250003"],
        "fee_categories": ["registration", "railway", "hotel"],
        "administrator_id": "admin-1",
        "project_info": "ACM competition project",
        "reimburser_info": "Lab reimbursement owner",
        "invoice_title": "同济大学",
        "tax_number": "12100000425006117D",
    }


def valid_task_update_payload(**overrides):
    return {
        "competition_name": "Updated ICPC Asia Regional",
        "competition_location": "Hangzhou",
        "competition_start_date": "2026-11-05",
        "competition_end_date": "2026-11-07",
        "deadline": "2026-12-10T00:00:00Z",
        "member_ids": ["2250001", "2250099"],
        "fee_categories": ["registration", "hotel"],
        "project_info": "Updated ACM competition project",
        "reimburser_info": "Updated reimbursement owner",
        "invoice_title": "更新后的同济大学",
        "tax_number": "91310000UPDATED0001",
    } | overrides


def upload_material(client: TestClient, task_id: str, filename: str = "ticket.pdf") -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": (filename, b"fake-pdf-content", "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def valid_invoice_payload():
    return {
        "actor_id": "2250001",
        "invoice_number": "INV-001",
        "issue_date": "2026-11-04",
        "transaction_time": "2026-11-01T08:00:00Z",
        "buyer_name": "同济大学",
        "tax_number": "12100000425006117D",
        "seller_name": "铁路服务商",
        "amount_cents": 12345,
        "expense_type": "railway",
    }


def create_invoice(client: TestClient, material_id: str, **overrides) -> str:
    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | overrides,
    )
    assert response.status_code == 201
    return response.json()["invoice"]["id"]


def replace_invoice_splits(client: TestClient, invoice_id: str) -> str:
    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={"actor_id": "2250001", "items": [{"member_id": "2250001", "amount_cents": 12345}]},
    )
    assert response.status_code == 200
    return response.json()["items"][0]["id"]


def confirm_split(client: TestClient, split_id: str) -> None:
    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={"actor_id": "2250001", "member_id": "2250001", "status": "confirmed"},
    )
    assert response.status_code == 200


def open_task(client: TestClient, task_id: str) -> None:
    response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert response.status_code == 200


def move_open_task_to_reviewing(client: TestClient, task_id: str) -> None:
    for target_status in ("closed", "reviewing"):
        response = client.patch(
            f"/api/tasks/{task_id}/status",
            json={"target_status": target_status},
            headers=admin_auth_headers(client),
        )
        assert response.status_code == 200


def test_health_check(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_task(tmp_path):
    client = make_client(tmp_path)

    created = client.post(
        "/api/tasks",
        json=valid_task_payload(),
        headers=admin_auth_headers(client),
    )

    assert created.status_code == 201
    body = created.json()
    assert body["id"]
    assert body["status"] == "draft"
    assert body["competition_name"] == "ICPC Asia Regional"
    assert body["invoice_title"] == "同济大学"

    fetched = client.get(
        f"/api/tasks/{body['id']}",
        headers=admin_auth_headers(client),
    )

    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_create_task_requires_authenticated_admin(tmp_path):
    client = make_client(tmp_path)

    anonymous_response = client.post("/api/tasks", json=valid_task_payload())
    assert_api_error(
        anonymous_response,
        status_code=401,
        code="unauthorized",
        detail="invalid or missing bearer token",
    )

    member_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )
    member_response = client.post(
        "/api/tasks",
        json=valid_task_payload() | {"administrator_id": "2250001"},
        headers=auth_headers(member_token),
    )
    assert_api_error(
        member_response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to create reimbursement tasks",
    )


def test_create_task_inherits_global_invoice_config(tmp_path):
    client = make_client(
        tmp_path,
        GlobalInvoiceConfig(
            invoice_title="同济大学电子与信息工程学院",
            tax_number="GLOBAL-TAX-NUMBER",
        ),
    )
    payload = valid_task_payload()
    payload.pop("invoice_title")
    payload.pop("tax_number")

    response = client.post("/api/tasks", json=payload, headers=admin_auth_headers(client))

    assert response.status_code == 201
    body = response.json()
    assert body["invoice_title"] == "同济大学电子与信息工程学院"
    assert body["tax_number"] == "GLOBAL-TAX-NUMBER"


def test_create_task_allows_task_level_invoice_override(tmp_path):
    client = make_client(
        tmp_path,
        GlobalInvoiceConfig(
            invoice_title="默认抬头",
            tax_number="DEFAULT-TAX",
        ),
    )
    payload = valid_task_payload() | {
        "invoice_title": "比赛专用抬头",
        "tax_number": "TASK-TAX-NUMBER",
    }

    response = client.post("/api/tasks", json=payload, headers=admin_auth_headers(client))

    assert response.status_code == 201
    body = response.json()
    assert body["invoice_title"] == "比赛专用抬头"
    assert body["tax_number"] == "TASK-TAX-NUMBER"


def test_create_task_rejects_missing_invoice_config_without_global_default(tmp_path):
    client = make_client(tmp_path)
    payload = valid_task_payload()
    payload.pop("invoice_title")
    payload.pop("tax_number")

    response = client.post("/api/tasks", json=payload, headers=admin_auth_headers(client))

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "missing invoice configuration fields: invoice_title, tax_number"
    )


def test_list_tasks_returns_created_tasks(tmp_path):
    client = make_client(tmp_path)
    first = valid_task_payload()
    second = valid_task_payload() | {"competition_name": "CCPC Final"}

    client.post("/api/tasks", json=first, headers=admin_auth_headers(client))
    client.post("/api/tasks", json=second, headers=admin_auth_headers(client))

    response = client.get("/api/tasks", headers=admin_auth_headers(client))

    assert response.status_code == 200
    assert [task["competition_name"] for task in response.json()] == [
        "ICPC Asia Regional",
        "CCPC Final",
    ]


def test_list_tasks_filters_by_member_id(tmp_path):
    client = make_client(tmp_path)
    create_task(client)
    create_task(
        client,
        payload=valid_task_payload() | {
        "competition_name": "CCPC Final",
        "member_ids": ["2250003", "2250999"],
        },
    )
    member_token = register_and_get_token(
        client,
        username="member-filter",
        role="member",
        actor_id="2250999",
        member_code="2250999",
    )

    response = client.get(
        "/api/tasks",
        params={"member_id": "2250999"},
        headers=auth_headers(member_token),
    )

    assert response.status_code == 200
    assert [task["competition_name"] for task in response.json()] == ["CCPC Final"]


def test_list_tasks_returns_empty_when_member_has_no_visible_tasks(tmp_path):
    client = make_client(tmp_path)
    create_task(client)
    member_token = register_and_get_token(
        client,
        username="member-empty",
        role="member",
        actor_id="2250888",
        member_code="2250888",
    )

    response = client.get(
        "/api/tasks",
        params={"member_id": "2250888"},
        headers=auth_headers(member_token),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_rejects_empty_member_list(tmp_path):
    client = make_client(tmp_path)
    payload = valid_task_payload() | {"member_ids": []}

    response = client.post("/api/tasks", json=payload, headers=admin_auth_headers(client))

    assert response.status_code == 422


def test_rejects_unsupported_fee_categories(tmp_path):
    client = make_client(tmp_path)
    payload = valid_task_payload() | {"fee_categories": ["registration", "meals"]}

    response = client.post("/api/tasks", json=payload, headers=admin_auth_headers(client))

    assert response.status_code == 422
    assert "unsupported fee categories: meals" in response.text


def test_rejects_end_date_before_start_date(tmp_path):
    client = make_client(tmp_path)
    payload = valid_task_payload() | {
        "competition_start_date": "2026-11-03",
        "competition_end_date": "2026-11-01",
    }

    response = client.post("/api/tasks", json=payload, headers=admin_auth_headers(client))

    assert response.status_code == 422


def test_rejects_past_deadline(tmp_path):
    client = make_client(tmp_path)
    past_deadline = datetime(2025, 1, 1, tzinfo=UTC).isoformat()
    payload = valid_task_payload() | {"deadline": past_deadline}

    response = client.post("/api/tasks", json=payload, headers=admin_auth_headers(client))

    assert response.status_code == 422


def test_get_missing_task_returns_404(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/tasks/missing", headers=admin_auth_headers(client))

    assert_api_error(
        response,
        status_code=404,
        code="not_found",
        detail="task not found",
    )


def test_get_task_members_returns_member_list(tmp_path):
    client = make_client(tmp_path)
    register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="member-actor-1",
        member_code="2250001",
    )
    register_and_get_token(
        client,
        username="member2",
        role="member",
        actor_id="member-actor-2",
        member_code="2250002",
    )
    created = create_task(client)

    response = client.get(
        f"/api/tasks/{created['id']}/members",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "member_id": "2250001",
                "username": "member1",
                "display_name": "member1",
                "student_id": "2250001",
            },
            {
                "member_id": "2250002",
                "username": "member2",
                "display_name": "member2",
                "student_id": "2250002",
            },
            {
                "member_id": "2250003",
                "username": None,
                "display_name": None,
                "student_id": "2250003",
            },
        ]
    }


def test_search_member_candidates_returns_matching_members(tmp_path):
    client = make_client(tmp_path)
    register_and_get_token(
        client,
        username="alice",
        role="member",
        actor_id="member-actor-1",
        member_code="2250001",
    )
    register_and_get_token(
        client,
        username="bob",
        role="member",
        actor_id="member-actor-2",
        member_code="2250002",
    )
    register_and_get_token(
        client,
        username="ops-admin",
        role="admin",
        actor_id="admin-ops",
        member_code=None,
    )

    response = client.get(
        "/api/tasks/search/member-candidates",
        params={"keyword": "225000"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "actor_id": "member-actor-1",
                "username": "alice",
                "display_name": "alice",
                "student_id": "2250001",
            },
            {
                "actor_id": "member-actor-2",
                "username": "bob",
                "display_name": "bob",
                "student_id": "2250002",
            },
        ]
    }


def test_search_member_candidates_rejects_non_administrator(tmp_path):
    client = make_client(tmp_path)
    member_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="member-actor-1",
        member_code="2250001",
    )

    response = client.get(
        "/api/tasks/search/member-candidates",
        params={"keyword": "2250001"},
        headers=auth_headers(member_token),
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to search task member candidates",
    )


def test_task_queries_require_bearer_and_enforce_scope(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)
    member_token = register_and_get_token(
        client,
        username="taskmember",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )
    outsider_admin_token = register_and_get_token(
        client,
        username="outsider-admin",
        role="admin",
        actor_id="admin-2",
        member_code=None,
    )

    for path in (
        f"/api/tasks/{task['id']}",
        f"/api/tasks/{task['id']}/members",
    ):
        anonymous_response = client.get(path)
        assert_api_error(
            anonymous_response,
            status_code=401,
            code="unauthorized",
            detail="invalid or missing bearer token",
        )

        member_response = client.get(path, headers=auth_headers(member_token))
        assert member_response.status_code == 200

        administrator_response = client.get(path, headers=admin_auth_headers(client))
        assert administrator_response.status_code == 200

        outsider_response = client.get(path, headers=auth_headers(outsider_admin_token))
        assert_api_error(
            outsider_response,
            status_code=403,
            code="forbidden",
            detail=(
                "actor is not allowed to view this task"
                if path.endswith(task["id"])
                else "actor is not allowed to view task members for this task"
            ),
        )


def test_administrator_can_record_and_list_material_reminders(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)

    create_response = client.post(
        f"/api/tasks/{task['id']}/material-reminders",
        json={
            "administrator_id": "admin-1",
            "member_id": "2250002",
            "content": "请补充支付记录和比赛通知。",
        },
        headers=admin_auth_headers(client),
    )

    assert create_response.status_code == 201
    reminder = create_response.json()
    assert reminder["task_id"] == task["id"]
    assert reminder["administrator_id"] == "admin-1"
    assert reminder["member_id"] == "2250002"
    assert reminder["content"] == "请补充支付记录和比赛通知。"
    assert reminder["created_at"]

    list_response = client.get(
        f"/api/tasks/{task['id']}/material-reminders",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert list_response.status_code == 200
    assert list_response.json() == {"items": [reminder]}


def test_create_material_reminder_rejects_non_administrator(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)
    member_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )

    response = client.post(
        f"/api/tasks/{task['id']}/material-reminders",
        json={
            "administrator_id": "2250001",
            "member_id": "2250002",
            "content": "请补充支付记录。",
        },
        headers=auth_headers(member_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to manage material reminders for this task"


def test_create_material_reminder_rejects_member_outside_task(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)

    response = client.post(
        f"/api/tasks/{task['id']}/material-reminders",
        json={
            "administrator_id": "admin-1",
            "member_id": "2250999",
            "content": "请补充订单截图。",
        },
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "submitter is not a member of the task: 2250999"


def test_list_material_reminders_rejects_non_administrator(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)
    create_response = client.post(
        f"/api/tasks/{task['id']}/material-reminders",
        json={
            "administrator_id": "admin-1",
            "member_id": "2250002",
            "content": "请补充比赛通知。",
        },
        headers=admin_auth_headers(client),
    )
    assert create_response.status_code == 201
    member_token = register_and_get_token(
        client,
        username="member2",
        role="member",
        actor_id="2250002",
        member_code="2250002",
    )

    response = client.get(
        f"/api/tasks/{task['id']}/material-reminders",
        params={"actor_id": "2250002"},
        headers=auth_headers(member_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to manage material reminders for this task"


def test_update_task_members_allows_replace_in_draft(tmp_path):
    client = make_client(tmp_path)
    register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="member-actor-1",
        member_code="2250001",
    )
    register_and_get_token(
        client,
        username="member3",
        role="member",
        actor_id="member-actor-3",
        member_code="2250003",
    )
    created = create_task(client)

    response = client.put(
        f"/api/tasks/{created['id']}/members",
        json={"member_ids": ["2250001", "2250003", "2250999"]},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "member_id": "2250001",
                "username": "member1",
                "display_name": "member1",
                "student_id": "2250001",
            },
            {
                "member_id": "2250003",
                "username": "member3",
                "display_name": "member3",
                "student_id": "2250003",
            },
            {
                "member_id": "2250999",
                "username": None,
                "display_name": None,
                "student_id": "2250999",
            },
        ]
    }

    fetched = client.get(
        f"/api/tasks/{created['id']}",
        headers=admin_auth_headers(client),
    )
    assert fetched.status_code == 200
    assert fetched.json()["member_ids"] == ["2250001", "2250003", "2250999"]


def test_update_task_allows_replace_in_draft(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)

    response = client.put(
        f"/api/tasks/{created['id']}",
        json=valid_task_update_payload(),
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["competition_name"] == "Updated ICPC Asia Regional"
    assert body["competition_location"] == "Hangzhou"
    assert body["member_ids"] == ["2250001", "2250099"]
    assert body["fee_categories"] == ["registration", "hotel"]
    assert body["project_info"] == "Updated ACM competition project"
    assert body["reimburser_info"] == "Updated reimbursement owner"
    assert body["invoice_title"] == "更新后的同济大学"
    assert body["tax_number"] == "91310000UPDATED0001"

    fetched = client.get(
        f"/api/tasks/{created['id']}",
        headers=admin_auth_headers(client),
    )
    assert fetched.status_code == 200
    assert fetched.json()["competition_name"] == "Updated ICPC Asia Regional"


def test_update_task_rejects_non_draft_task(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)
    client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )

    response = client.put(
        f"/api/tasks/{created['id']}",
        json=valid_task_update_payload(),
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "task can only be updated while it is draft"


def test_update_task_rejects_non_owner(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)
    outsider_admin_headers = auth_headers(
        register_and_get_token(
            client,
            username="other-admin",
            role="admin",
            actor_id="admin-2",
            member_code=None,
        )
    )

    response = client.put(
        f"/api/tasks/{created['id']}",
        json=valid_task_update_payload(),
        headers=outsider_admin_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to update this task"


def test_update_task_members_rejects_non_draft_task(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)
    client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )

    response = client.put(
        f"/api/tasks/{created['id']}/members",
        json={"member_ids": ["2250001", "2250999"]},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "task members can only be updated while task is draft"


def test_update_missing_task_members_returns_404(tmp_path):
    client = make_client(tmp_path)

    response = client.put(
        "/api/tasks/missing/members",
        json={"member_ids": ["2250001"]},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


def test_update_task_status_allows_valid_transition(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)

    response = client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "open"


def test_update_task_status_allows_transition_from_closed_to_reviewing(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)
    open_task(client, task["id"])

    closed = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "closed"},
        headers=admin_auth_headers(client),
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    reviewing = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "reviewing"},
        headers=admin_auth_headers(client),
    )

    assert reviewing.status_code == 200
    assert reviewing.json()["status"] == "reviewing"


def test_update_task_status_rejects_open_when_member_list_missing(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)
    update_task_row(tmp_path, created["id"], member_ids=[])

    response = client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "task is missing required publish fields: member_ids"


def test_update_task_status_rejects_open_when_fee_categories_missing(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)
    update_task_row(tmp_path, created["id"], fee_categories=[])

    response = client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "task is missing required publish fields: fee_categories"
    )


def test_update_task_status_rejects_open_when_project_info_missing(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)
    update_task_row(tmp_path, created["id"], project_info="   ")

    response = client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "task is missing required publish fields: project_info"


def test_update_task_status_rejects_open_when_reimburser_info_missing(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)
    update_task_row(tmp_path, created["id"], reimburser_info="   ")

    response = client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "task is missing required publish fields: reimburser_info"
    )


def test_update_task_status_rejects_invalid_transition(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)

    response = client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "completed"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert "cannot transition task" in response.json()["detail"]


def test_update_task_status_allows_ready_to_export_after_review_conditions_met(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)
    open_task(client, task["id"])
    material_id = upload_material(client, task["id"])
    invoice_id = create_invoice(client, material_id)
    split_id = replace_invoice_splits(client, invoice_id)
    confirm_split(client, split_id)
    move_open_task_to_reviewing(client, task["id"])

    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready_to_export"


def test_update_task_status_allows_ready_to_export_when_only_warning_validations_remain(
    tmp_path,
):
    client = make_client(tmp_path)
    task = create_task(client)
    open_task(client, task["id"])
    material_id = upload_material(client, task["id"])
    invoice_id = create_invoice(
        client,
        material_id,
        transaction_time="2026-10-29T08:00:00Z",
    )
    split_id = replace_invoice_splits(client, invoice_id)
    confirm_split(client, split_id)
    move_open_task_to_reviewing(client, task["id"])

    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready_to_export"


def test_update_task_status_rejects_ready_to_export_when_blocker_validation_fails(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)
    open_task(client, task["id"])
    material_id = upload_material(client, task["id"])
    invoice_id = create_invoice(client, material_id, buyer_name="错误抬头")
    split_id = replace_invoice_splits(client, invoice_id)
    confirm_split(client, split_id)
    move_open_task_to_reviewing(client, task["id"])

    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"task review is incomplete: blocker validations are not resolved for invoices: {invoice_id}"
    )


def test_update_task_status_rejects_paper_invoice_before_admin_receipt_and_allows_after_confirmation(
    tmp_path,
):
    client = make_client(tmp_path)
    task = create_task(client)
    open_task(client, task["id"])
    member_token = register_and_get_token(
        client,
        username="paper-ready-member",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )
    create_response = client.post(
        f"/api/tasks/{task['id']}/paper-invoices",
        json=valid_invoice_payload() | {
            "invoice_number": "PAPER-READY-001",
            "expense_type": "railway",
            "amount_cents": 12345,
        },
        headers=auth_headers(member_token),
    )
    assert create_response.status_code == 201
    invoice_id = create_response.json()["invoice"]["id"]
    split_id = replace_invoice_splits(client, invoice_id)
    confirm_split(client, split_id)
    move_open_task_to_reviewing(client, task["id"])

    blocked_response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )

    assert blocked_response.status_code == 409
    assert blocked_response.json()["detail"] == (
        f"task review is incomplete: blocker validations are not resolved for invoices: {invoice_id}"
    )

    confirm_receipt_response = client.put(
        f"/api/invoices/{invoice_id}/paper-receipt",
        json={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )
    assert confirm_receipt_response.status_code == 200

    ready_response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )

    assert ready_response.status_code == 200
    assert ready_response.json()["status"] == "ready_to_export"


def test_update_task_status_rejects_ready_to_export_when_member_confirmation_missing(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)
    open_task(client, task["id"])
    material_id = upload_material(client, task["id"])
    invoice_id = create_invoice(client, material_id)
    split_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={"actor_id": "2250001", "items": [{"member_id": "2250002", "amount_cents": 12345}]},
    )
    assert split_response.status_code == 200
    split_id = split_response.json()["items"][0]["id"]
    move_open_task_to_reviewing(client, task["id"])

    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "task review is incomplete: "
        f"member confirmations are still missing for splits: {split_id}"
    )


def test_update_task_status_rejects_ready_to_export_when_member_confirmation_is_disputed(
    tmp_path,
):
    client = make_client(tmp_path)
    task = create_task(client)
    open_task(client, task["id"])
    material_id = upload_material(client, task["id"])
    invoice_id = create_invoice(client, material_id)
    split_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 6000},
                {"member_id": "2250002", "amount_cents": 6345},
            ],
        },
    )
    assert split_response.status_code == 200
    split_ids = {item["member_id"]: item["id"] for item in split_response.json()["items"]}

    confirmed_response = client.put(
        f"/api/splits/{split_ids['2250001']}/confirmation",
        json={"actor_id": "2250001", "member_id": "2250001", "status": "confirmed"},
    )
    assert confirmed_response.status_code == 200

    disputed_response = client.put(
        f"/api/splits/{split_ids['2250002']}/confirmation",
        json={
            "actor_id": "2250002",
            "member_id": "2250002",
            "status": "disputed",
            "dispute_reason": "shared amount should be lower",
        },
    )
    assert disputed_response.status_code == 200

    move_open_task_to_reviewing(client, task["id"])

    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "task review is incomplete: "
        f"member confirmations are disputed for splits: {split_ids['2250002']}"
    )


def test_update_task_status_rejects_ready_to_export_when_pending_assignment_material_exists(
    tmp_path,
):
    client = make_client(tmp_path)
    task = create_task(client)
    open_task(client, task["id"])
    material_id = upload_material(client, task["id"])
    invoice_id = create_invoice(client, material_id)
    split_id = replace_invoice_splits(client, invoice_id)
    confirm_split(client, split_id)
    pending_assignment_response = client.post(
        "/api/materials/pending-assignment",
        data={
            "task_id_hint": task["id"],
            "submitter_id_hint": "2250002",
            "channel": "email",
            "material_type": "other_attachment",
        },
        files={"files": ("notice.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert pending_assignment_response.status_code == 201
    pending_material_id = pending_assignment_response.json()["items"][0]["id"]
    move_open_task_to_reviewing(client, task["id"])

    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "task review is incomplete: "
        "pending-assignment materials must be claimed before final confirmation "
        f"(count: 1, material_ids: {pending_material_id})"
    )


def test_update_task_status_rejects_ready_to_export_when_split_amount_changes_after_confirmation(
    tmp_path,
):
    client = make_client(tmp_path)
    task = create_task(client)
    open_task(client, task["id"])
    material_id = upload_material(client, task["id"])
    invoice_id = create_invoice(client, material_id)

    initial_split_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 6000},
                {"member_id": "2250002", "amount_cents": 6345},
            ],
        },
    )
    assert initial_split_response.status_code == 200
    split_ids = {item["member_id"]: item["id"] for item in initial_split_response.json()["items"]}

    for member_id, split_id in split_ids.items():
        response = client.put(
            f"/api/splits/{split_id}/confirmation",
            json={"actor_id": member_id, "member_id": member_id, "status": "confirmed"},
        )
        assert response.status_code == 200

    replace_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "admin-1",
            "items": [
                {"member_id": "2250001", "amount_cents": 6100},
                {"member_id": "2250002", "amount_cents": 6245},
            ],
        },
    )
    assert replace_response.status_code == 200
    assert {item["member_id"]: item["id"] for item in replace_response.json()["items"]} == split_ids

    move_open_task_to_reviewing(client, task["id"])

    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "task review is incomplete: "
        "member confirmations are still pending for splits: "
        f"{split_ids['2250001']}, {split_ids['2250002']}"
    )


def test_update_task_status_rejects_completed_before_export_completion_is_recorded(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)
    open_task(client, task["id"])
    material_id = upload_material(client, task["id"])
    invoice_id = create_invoice(client, material_id)
    split_id = replace_invoice_splits(client, invoice_id)
    confirm_split(client, split_id)
    move_open_task_to_reviewing(client, task["id"])
    ready = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )
    assert ready.status_code == 200

    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "completed"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "task cannot transition to completed before export completion is recorded"
    )


def test_update_missing_task_status_returns_404(tmp_path):
    client = make_client(tmp_path)

    response = client.patch(
        "/api/tasks/missing/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


def test_run_task_deadline_check_closes_expired_open_task(tmp_path):
    client = make_client(tmp_path)
    created = create_task(client)
    client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    update_task_row(
        tmp_path,
        created["id"],
        deadline=datetime.now(UTC) - timedelta(seconds=1),
    )

    response = client.post("/api/tasks/deadline-check")

    assert response.status_code == 200
    assert response.json() == {
        "closed_count": 1,
        "closed_task_ids": [created["id"]],
    }

    fetched = client.get(
        f"/api/tasks/{created['id']}",
        headers=admin_auth_headers(client),
    )
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "closed"


def test_run_task_deadline_check_ignores_non_open_tasks(tmp_path):
    client = make_client(tmp_path)
    draft_task = create_task(client)
    open_task = create_task(
        client,
        payload=valid_task_payload() | {"competition_name": "CCPC Final"},
    )
    client.patch(
        f"/api/tasks/{open_task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    update_task_row(
        tmp_path,
        draft_task["id"],
        deadline=datetime.now(UTC) - timedelta(seconds=1),
    )

    response = client.post("/api/tasks/deadline-check")

    assert response.status_code == 200
    assert response.json() == {
        "closed_count": 0,
        "closed_task_ids": [],
    }

    fetched = client.get(
        f"/api/tasks/{draft_task['id']}",
        headers=admin_auth_headers(client),
    )
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "draft"


def test_task_persists_across_app_instances(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    first_client = TestClient(
        create_app(database_url, material_file_storage=LocalMaterialFileStorage(tmp_path / "first"))
    )
    task = create_task(first_client)

    second_client = TestClient(
        create_app(
            database_url,
            material_file_storage=LocalMaterialFileStorage(tmp_path / "second"),
        )
    )
    response = second_client.get(
        f"/api/tasks/{task['id']}",
        headers=admin_auth_headers(second_client),
    )

    assert response.status_code == 200
    assert response.json()["id"] == task["id"]
