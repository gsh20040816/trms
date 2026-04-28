import json

from trms_cli.cli import CLI_JSON_SCHEMA_VERSION, build_cli_request_headers, main


def test_health_command_reports_ok(monkeypatch, capsys):
    seen = {}

    def fake_fetch_json(url: str, *, headers=None):
        seen["url"] = url
        seen["headers"] = headers
        return 200, {"status": "ok"}

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["health", "--base-url", "http://example.com/api"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert seen["url"] == "http://example.com/api/health"
    assert seen["headers"] == build_cli_request_headers()
    assert captured.out == "TRMS API health: ok\n"
    assert captured.err == ""


def test_health_command_reports_error(monkeypatch, capsys):
    def fake_fetch_json(_url: str, *, headers=None):
        assert headers == build_cli_request_headers()
        return 200, {"status": "degraded"}

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["health"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "Error: TRMS API health payload is not ready\n"


def test_health_command_reports_ok_as_json(monkeypatch, capsys):
    def fake_fetch_json(_url: str, *, headers=None):
        assert headers == build_cli_request_headers()
        return 200, {"status": "ok"}

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["health", "--base-url", "http://example.com/api/", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": True,
        "command": "health",
        "data": {
            "status": "ok",
            "base_url": "http://example.com/api",
        },
    }


def test_health_command_reports_error_as_json(monkeypatch, capsys):
    def fake_fetch_json(_url: str, *, headers=None):
        assert headers == build_cli_request_headers()
        return 200, {"status": "degraded"}

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["health", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": False,
        "command": "health",
        "error": {
            "code": "health_not_ready",
            "message": "TRMS API health payload is not ready",
        },
    }
