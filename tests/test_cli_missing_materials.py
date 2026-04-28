import json

from trms_cli.cli import CLI_JSON_SCHEMA_VERSION, build_cli_request_headers, main
from trms_cli.token_store import save_token_session


def sample_missing_materials_payload() -> dict[str, object]:
    return {
        "task_id": "task-123",
        "actor_id": "2250001",
        "scope": "member",
        "items": [
            {
                "task_id": "task-123",
                "member_id": "2250001",
                "invoice_id": "invoice-001",
                "invoice_number": "REG-001",
                "expense_type": "registration",
                "required_material_type": "competition_notice",
                "source_rule_code": "invoice_competition_notice_required",
                "message": "报名费缺少比赛通知",
                "evidence": {},
                "detected_at": "2026-04-28T11:31:00Z",
            },
            {
                "task_id": "task-123",
                "member_id": "2250001",
                "invoice_id": "invoice-001",
                "invoice_number": "REG-001",
                "expense_type": "registration",
                "required_material_type": "payment_record",
                "source_rule_code": "invoice_payment_record_required",
                "message": "发票金额达到阈值，缺少支付记录",
                "evidence": {},
                "detected_at": "2026-04-28T11:31:00Z",
            },
        ],
    }


def test_missing_materials_command_reports_text(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_fetch_json(url: str, *, headers=None):
        assert url == "http://127.0.0.1:8000/api/tasks/task-123/missing-materials"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        return 200, sample_missing_materials_payload()

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["missing-materials", "--task-id", "task-123"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == (
        "Missing materials for task task-123 member 2250001\n"
        "Count: 2\n"
        "invoice_number\trequired_material_type\tmessage\n"
        "REG-001\tcompetition_notice\t报名费缺少比赛通知\n"
        "REG-001\tpayment_record\t发票金额达到阈值，缺少支付记录\n"
    )


def test_missing_materials_command_reports_json_with_empty_items(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://example.com/api",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_fetch_json(url: str, *, headers=None):
        assert url == "http://example.com/api/tasks/task-123/missing-materials"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        return 200, {
            "task_id": "task-123",
            "actor_id": "2250001",
            "scope": "member",
            "items": [],
        }

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["missing-materials", "--task-id", "task-123", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": True,
        "command": "missing-materials",
        "data": {
            "base_url": "http://example.com/api",
            "task_id": "task-123",
            "member_id": "2250001",
            "scope": "member",
            "count": 0,
            "items": [],
        },
    }


def test_missing_materials_command_requires_login_session(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(tmp_path / "config"))

    exit_code = main(["missing-materials", "--task-id", "task-123", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": False,
        "command": "missing-materials",
        "error": {
            "code": "login_required",
            "message": "CLI token session not found; run `trms-cli login` first",
        },
    }
