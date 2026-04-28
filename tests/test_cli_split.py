import json

from trms_cli.cli import CLI_JSON_SCHEMA_VERSION, CliError, build_cli_request_headers, main
from trms_cli.token_store import save_token_session


def test_split_command_submits_invoice_splits(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_put_json(url: str, *, headers=None, payload=None):
        assert url == "http://127.0.0.1:8000/api/invoices/invoice-001/splits"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        assert payload == {
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 6000},
                {"member_id": "2250002", "amount_cents": 6345},
            ],
        }
        return 200, {
            "items": [
                {
                    "id": "split-001",
                    "invoice_id": "invoice-001",
                    "member_id": "2250001",
                    "amount_cents": 6000,
                    "note": "self paid",
                    "version": 1,
                },
                {
                    "id": "split-002",
                    "invoice_id": "invoice-001",
                    "member_id": "2250002",
                    "amount_cents": 6345,
                    "note": None,
                    "version": 1,
                },
            ]
        }

    monkeypatch.setattr("trms_cli.cli.put_json", fake_put_json)

    exit_code = main(
        [
            "split",
            "--invoice-id",
            "invoice-001",
            "--member",
            "2250001:6000",
            "--member",
            "2250002:6345",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == (
        "Updated splits for invoice invoice-001\n"
        "Count: 2\n"
        "split_id\tmember_id\tamount_cents\tversion\tnote\n"
        "split-001\t2250001\t6000\t1\tself paid\n"
        "split-002\t2250002\t6345\t1\t\n"
    )


def test_split_command_reports_json(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://example.com/api",
        member_id="2250002",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_put_json(url: str, *, headers=None, payload=None):
        assert url == "http://example.com/api/invoices/invoice-002/splits"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        assert payload == {
            "actor_id": "2250002",
            "items": [{"member_id": "2250002", "amount_cents": 12345}],
        }
        return 200, {
            "items": [
                {
                    "id": "split-010",
                    "invoice_id": "invoice-002",
                    "member_id": "2250002",
                    "amount_cents": 12345,
                    "note": None,
                    "version": 1,
                }
            ]
        }

    monkeypatch.setattr("trms_cli.cli.put_json", fake_put_json)

    exit_code = main(
        [
            "split",
            "--invoice-id",
            "invoice-002",
            "--member",
            "2250002:12345",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": True,
        "command": "split",
        "data": {
            "base_url": "http://example.com/api",
            "invoice_id": "invoice-002",
            "member_id": "2250002",
            "item_count": 1,
            "items": [
                {
                    "id": "split-010",
                    "invoice_id": "invoice-002",
                    "member_id": "2250002",
                    "amount_cents": 12345,
                    "note": None,
                    "version": 1,
                }
            ],
        },
    }


def test_split_command_shows_backend_amount_mismatch_error(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )
    seen = {}

    def fake_put_json(url: str, *, headers=None, payload=None):
        seen["url"] = url
        seen["headers"] = headers
        seen["payload"] = payload
        raise CliError(
            "request failed with status 409: split amount total must equal invoice amount",
            code="http_error",
        )

    monkeypatch.setattr("trms_cli.cli.put_json", fake_put_json)

    exit_code = main(
        [
            "split",
            "--invoice-id",
            "invoice-003",
            "--member",
            "2250001:6000",
            "--member",
            "2250002:100",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert seen["url"] == "http://127.0.0.1:8000/api/invoices/invoice-003/splits"
    assert seen["headers"] == build_cli_request_headers(access_token="stored-access-token")
    assert seen["payload"] == {
        "actor_id": "2250001",
        "items": [
            {"member_id": "2250001", "amount_cents": 6000},
            {"member_id": "2250002", "amount_cents": 100},
        ],
    }
    assert captured.err == (
        "Error: request failed with status 409: "
        "split amount total must equal invoice amount\n"
    )


def test_split_command_requires_login_session(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(tmp_path / "config"))

    exit_code = main(
        [
            "split",
            "--invoice-id",
            "invoice-004",
            "--member",
            "2250001:12345",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": False,
        "command": "split",
        "error": {
            "code": "login_required",
            "message": "CLI token session not found; run `trms-cli login` first",
        },
    }
