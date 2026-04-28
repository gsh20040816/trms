import json
import os
import stat

from trms_cli.cli import CLI_JSON_SCHEMA_VERSION, main
from trms_cli.token_store import TOKEN_STORE_FILENAME


def test_login_command_stores_tokens_without_printing_secrets(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    member_id = "2250001"
    access_token = "access-secret-token"
    refresh_token = "refresh-secret-token"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("TRMS_CLI_ACCESS_TOKEN", access_token)
    monkeypatch.setenv("TRMS_CLI_REFRESH_TOKEN", refresh_token)

    exit_code = main(["login", "--base-url", "http://example.com/api/", "--member-id", member_id])

    captured = capsys.readouterr()
    token_store_path = config_dir / TOKEN_STORE_FILENAME
    assert exit_code == 0
    assert access_token not in captured.out
    assert refresh_token not in captured.out
    assert access_token not in captured.err
    assert refresh_token not in captured.err
    assert captured.out == f"Stored TRMS CLI session for member {member_id} at {token_store_path}\n"
    assert captured.err == ""

    with token_store_path.open(encoding="utf-8") as stream:
        assert json.load(stream) == {
            "schema_version": "trms-cli.session.v1",
            "base_url": "http://example.com/api",
            "member_id": member_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    if os.name != "nt":
        assert stat.S_IMODE(token_store_path.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(token_store_path.stat().st_mode) == 0o600


def test_login_command_reports_json_without_printing_secrets(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    member_id = "2250002"
    access_token = "json-access-token"
    refresh_token = "json-refresh-token"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("TRMS_CLI_ACCESS_TOKEN", access_token)
    monkeypatch.setenv("TRMS_CLI_REFRESH_TOKEN", refresh_token)

    exit_code = main(["login", "--member-id", member_id, "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert access_token not in captured.out
    assert refresh_token not in captured.out
    assert access_token not in captured.err
    assert refresh_token not in captured.err
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": True,
        "command": "login",
        "data": {
            "base_url": "http://127.0.0.1:8000",
            "member_id": member_id,
            "token_store_backend": "local_file",
            "token_store_path": str(config_dir / TOKEN_STORE_FILENAME),
        },
    }


def test_login_command_requires_noninteractive_token_source(monkeypatch, capsys):
    monkeypatch.delenv("TRMS_CLI_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("TRMS_CLI_REFRESH_TOKEN", raising=False)
    monkeypatch.setattr("trms_cli.cli.is_interactive_input", lambda: False)

    exit_code = main(["login", "--member-id", "2250001", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": False,
        "command": "login",
        "error": {
            "code": "login_token_missing",
            "message": "TRMS_CLI_ACCESS_TOKEN is not set and CLI cannot prompt in non-interactive mode",
        },
    }
