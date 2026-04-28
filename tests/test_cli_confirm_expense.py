import json

from trms_cli.cli import CLI_JSON_SCHEMA_VERSION, build_cli_request_headers, main
from trms_cli.token_store import save_token_session


def sample_expense_detail_payload() -> dict[str, object]:
    return {
        "actor_id": "2250001",
        "scope": "member",
        "total_amount_cents": 100000,
        "items": [
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


def test_confirm_expense_command_lists_current_member_expense_details(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_fetch_json(url: str, *, headers=None):
        assert url == "http://127.0.0.1:8000/api/tasks/task-123/expense-details?actor_id=2250001"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        return 200, sample_expense_detail_payload()

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["confirm-expense", "--task-id", "task-123"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == (
        "Expense details for task task-123 member 2250001\n"
        "Count: 1 (total 100000 cents)\n"
        "split_id\tsplit_version\tinvoice_number\tamount_cents\tconfirmation_status\n"
        "split-001\t1\tREG-001\t100000\tmissing\n"
    )


def test_confirm_expense_command_submits_confirmed_status_and_reports_json(
    monkeypatch, tmp_path, capsys
):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://example.com/api",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_fetch_json(url: str, *, headers=None):
        assert url == "http://example.com/api/tasks/task-123/expense-details?actor_id=2250001"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        return 200, sample_expense_detail_payload()

    def fake_put_json(url: str, *, headers=None, payload=None):
        assert url == "http://example.com/api/splits/split-001/confirmation"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        assert payload == {
            "actor_id": "2250001",
            "member_id": "2250001",
            "status": "confirmed",
            "dispute_reason": None,
        }
        return 200, {
            "id": "confirmation-001",
            "split_id": "split-001",
            "member_id": "2250001",
            "split_version": 1,
            "split_amount_cents": 100000,
            "split_note": "self paid",
            "status": "confirmed",
            "dispute_reason": None,
            "confirmed_at": "2026-04-28T11:33:00Z",
            "updated_at": "2026-04-28T11:33:00Z",
            "is_current": True,
        }

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)
    monkeypatch.setattr("trms_cli.cli.put_json", fake_put_json)

    exit_code = main(
        [
            "confirm-expense",
            "--task-id",
            "task-123",
            "--split-id",
            "split-001",
            "--split-version",
            "1",
            "--status",
            "confirmed",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": True,
        "command": "confirm-expense",
        "data": {
            "base_url": "http://example.com/api",
            "mode": "submit",
            "task_id": "task-123",
            "member_id": "2250001",
            "item": {
                "split_id": "split-001",
                "member_id": "2250001",
                "split_version": 1,
                "status": "confirmed",
                "dispute_reason": None,
                "is_current": True,
            },
        },
    }


def test_confirm_expense_command_submits_dispute_reason(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_fetch_json(url: str, *, headers=None):
        assert url == "http://127.0.0.1:8000/api/tasks/task-123/expense-details?actor_id=2250001"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        return 200, sample_expense_detail_payload()

    def fake_put_json(url: str, *, headers=None, payload=None):
        assert url == "http://127.0.0.1:8000/api/splits/split-001/confirmation"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        assert payload == {
            "actor_id": "2250001",
            "member_id": "2250001",
            "status": "disputed",
            "dispute_reason": "amount is wrong",
        }
        return 200, {
            "id": "confirmation-002",
            "split_id": "split-001",
            "member_id": "2250001",
            "split_version": 1,
            "split_amount_cents": 100000,
            "split_note": "self paid",
            "status": "disputed",
            "dispute_reason": "amount is wrong",
            "confirmed_at": "2026-04-28T11:33:00Z",
            "updated_at": "2026-04-28T11:33:00Z",
            "is_current": True,
        }

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)
    monkeypatch.setattr("trms_cli.cli.put_json", fake_put_json)

    exit_code = main(
        [
            "confirm-expense",
            "--task-id",
            "task-123",
            "--split-id",
            "split-001",
            "--split-version",
            "1",
            "--status",
            "disputed",
            "--dispute-reason",
            "amount is wrong",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == (
        "Submitted expense confirmation for split split-001 version 1: disputed\n"
        "Dispute reason: amount is wrong\n"
    )


def test_confirm_expense_command_rejects_stale_split_version(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )
    payload = sample_expense_detail_payload()
    payload["items"][0]["split_version"] = 2

    def fake_fetch_json(url: str, *, headers=None):
        assert url == "http://127.0.0.1:8000/api/tasks/task-123/expense-details?actor_id=2250001"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        return 200, payload

    def fail_put_json(*args, **kwargs):
        raise AssertionError("put_json should not be called when split version is stale")

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)
    monkeypatch.setattr("trms_cli.cli.put_json", fail_put_json)

    exit_code = main(
        [
            "confirm-expense",
            "--task-id",
            "task-123",
            "--split-id",
            "split-001",
            "--split-version",
            "1",
            "--status",
            "confirmed",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == (
        "Error: expense detail version is stale; expected 1, current 2. "
        "Rerun `trms-cli confirm-expense --task-id task-123` to refresh\n"
    )


def test_confirm_expense_command_requires_login_session(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(tmp_path / "config"))

    exit_code = main(["confirm-expense", "--task-id", "task-123", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": False,
        "command": "confirm-expense",
        "error": {
            "code": "login_required",
            "message": "CLI token session not found; run `trms-cli login` first",
        },
    }
