import json

from trms_cli.cli import CLI_JSON_SCHEMA_VERSION, build_cli_request_headers, main
from trms_cli.token_store import save_token_session


def sample_status_payload() -> dict[str, object]:
    return {
        "task_id": "task-123",
        "actor_id": "2250001",
        "total_expense_amount_cents": 100000,
        "counts": {
            "material_count": 1,
            "missing_material_count": 2,
            "expense_detail_count": 1,
            "recognition_pending_count": 0,
            "recognition_succeeded_count": 0,
            "recognition_failed_count": 0,
            "recognition_needs_confirmation_count": 1,
            "validation_passed_count": 0,
            "validation_failed_count": 1,
            "validation_pending_count": 0,
            "validation_not_applicable_count": 0,
            "confirmed_expense_count": 0,
            "pending_confirmation_count": 0,
            "disputed_confirmation_count": 0,
            "missing_confirmation_count": 1,
        },
        "materials": [
            {
                "material_id": "material-001",
                "submitter_id": "2250001",
                "material_type": "invoice",
                "original_filename": "registration.pdf",
                "material_status": "assigned",
                "recognition_status": "needs_confirmation",
                "recognition_failure_stage": None,
                "recognition_failure_reason": None,
                "invoice_id": "invoice-001",
                "invoice_number": "REG-001",
                "validation_status": "failed",
                "validation_messages": [
                    "发票金额达到阈值，缺少支付记录",
                    "报名费缺少比赛通知",
                ],
                "created_at": "2026-04-28T11:30:00Z",
            }
        ],
        "missing_materials": [
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
        "expense_details": [
            {
                "split_id": "split-001",
                "split_version": 1,
                "member_id": "2250001",
                "amount_cents": 100000,
                "note": "self paid",
                "created_at": "2026-04-28T11:32:00Z",
                "updated_at": "2026-04-28T11:32:00Z",
                "invoice": {
                    "id": "invoice-001",
                    "material_id": "material-001",
                    "invoice_number": "REG-001",
                    "issue_date": "2026-11-04",
                    "transaction_time": "2026-11-01T08:00:00Z",
                    "buyer_name": "同济大学",
                    "seller_name": "服务商",
                    "amount_cents": 150000,
                    "expense_type": "registration",
                    "created_at": "2026-04-28T11:32:00Z",
                    "updated_at": "2026-04-28T11:32:00Z",
                },
                "confirmation": None,
            }
        ],
    }


def test_status_command_reports_text(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_fetch_json(url: str, *, headers=None):
        assert url == "http://127.0.0.1:8000/api/tasks/task-123/member-status?actor_id=2250001"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        return 200, sample_status_payload()

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["status", "--task-id", "task-123"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == (
        "Task status for task task-123 member 2250001\n"
        "Materials: 1\n"
        "material_id\tfilename\ttype\trecognition\tvalidation\tinvoice_number\n"
        "material-001\tregistration.pdf\tinvoice\tneeds_confirmation\tfailed\tREG-001\n"
        "Missing materials: 2\n"
        "invoice_number\trequired_material_type\tmessage\n"
        "REG-001\tcompetition_notice\t报名费缺少比赛通知\n"
        "REG-001\tpayment_record\t发票金额达到阈值，缺少支付记录\n"
        "Expense confirmations: 1 (total 100000 cents)\n"
        "split_id\tinvoice_number\tamount_cents\tconfirmation_status\n"
        "split-001\tREG-001\t100000\tmissing\n"
    )


def test_status_command_reports_json(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://example.com/api",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_fetch_json(url: str, *, headers=None):
        assert url == "http://example.com/api/tasks/task-123/member-status?actor_id=2250001"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        return 200, sample_status_payload()

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["status", "--task-id", "task-123", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": True,
        "command": "status",
        "data": {
            "base_url": "http://example.com/api",
            "task_id": "task-123",
            "member_id": "2250001",
            "total_expense_amount_cents": 100000,
            "counts": sample_status_payload()["counts"],
            "materials": [
                {
                    "material_id": "material-001",
                    "original_filename": "registration.pdf",
                    "material_type": "invoice",
                    "material_status": "assigned",
                    "recognition_status": "needs_confirmation",
                    "validation_status": "failed",
                    "invoice_id": "invoice-001",
                    "invoice_number": "REG-001",
                    "validation_messages": [
                        "发票金额达到阈值，缺少支付记录",
                        "报名费缺少比赛通知",
                    ],
                }
            ],
            "missing_materials": [
                {
                    "invoice_id": "invoice-001",
                    "invoice_number": "REG-001",
                    "required_material_type": "competition_notice",
                    "message": "报名费缺少比赛通知",
                },
                {
                    "invoice_id": "invoice-001",
                    "invoice_number": "REG-001",
                    "required_material_type": "payment_record",
                    "message": "发票金额达到阈值，缺少支付记录",
                },
            ],
            "expense_details": [
                {
                    "split_id": "split-001",
                    "invoice_id": "invoice-001",
                    "invoice_number": "REG-001",
                    "amount_cents": 100000,
                    "confirmation_status": None,
                    "dispute_reason": None,
                }
            ],
        },
    }


def test_status_command_requires_login_session(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(tmp_path / "config"))

    exit_code = main(["status", "--task-id", "task-123", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": False,
        "command": "status",
        "error": {
            "code": "login_required",
            "message": "CLI token session not found; run `trms-cli login` first",
        },
    }
