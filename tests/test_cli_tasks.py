import json

from trms_cli.cli import CLI_JSON_SCHEMA_VERSION, build_cli_request_headers, main
from trms_cli.token_store import save_token_session


def test_tasks_command_lists_open_tasks_from_stored_session(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://example.com/api",
        member_id="2250001",
        access_token="access-token",
        refresh_token="refresh-token",
    )
    future_deadline = "2099-12-31T23:59:59Z"
    seen = {}

    def fake_fetch_json(url: str, *, headers=None):
        seen["url"] = url
        seen["headers"] = headers
        return 200, [
            {
                "id": "task-open",
                "competition_name": "ICPC Asia Regional",
                "status": "open",
                "deadline": future_deadline,
            },
            {
                "id": "task-closed",
                "competition_name": "CCPC Final",
                "status": "closed",
                "deadline": future_deadline,
            },
            {
                "id": "task-expired",
                "competition_name": "XCPC Invitational",
                "status": "open",
                "deadline": "2020-01-01T00:00:00Z",
            },
        ]

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["tasks"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert seen["url"] == "http://example.com/api/tasks?member_id=2250001"
    assert seen["headers"] == build_cli_request_headers(access_token="access-token")
    assert captured.err == ""
    assert captured.out == (
        "task_id\tcompetition_name\tstatus\tdeadline\n"
        f"task-open\tICPC Asia Regional\topen\t{future_deadline}\n"
    )


def test_tasks_command_reports_json(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250002",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_fetch_json(url: str, *, headers=None):
        assert url == "http://127.0.0.1:8000/api/tasks?member_id=2250002"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        return 200, [
            {
                "id": "task-001",
                "competition_name": "ICPC Asia Regional",
                "status": "open",
                "deadline": "2099-12-31T23:59:59Z",
            }
        ]

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["tasks", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": True,
        "command": "tasks",
        "data": {
            "base_url": "http://127.0.0.1:8000",
            "member_id": "2250002",
            "count": 1,
            "items": [
                {
                    "id": "task-001",
                    "competition_name": "ICPC Asia Regional",
                    "status": "open",
                    "deadline": "2099-12-31T23:59:59Z",
                }
            ],
        },
    }


def test_tasks_command_requires_login_session(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(tmp_path / "config"))

    exit_code = main(["tasks", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": False,
        "command": "tasks",
        "error": {
            "code": "login_required",
            "message": "CLI token session not found; run `trms-cli login` first",
        },
    }


def test_tasks_command_reports_no_visible_tasks(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250999",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_fetch_json(url: str, *, headers=None):
        assert url == "http://127.0.0.1:8000/api/tasks?member_id=2250999"
        assert headers == build_cli_request_headers(access_token="stored-access-token")
        return 200, []

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["tasks"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == "No current submission tasks.\n"
