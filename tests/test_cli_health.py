from trms_cli.cli import main


def test_health_command_reports_ok(monkeypatch, capsys):
    seen = {}

    def fake_fetch_json(url: str):
        seen["url"] = url
        return 200, {"status": "ok"}

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["health", "--base-url", "http://example.com/api"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert seen["url"] == "http://example.com/api/health"
    assert captured.out == "TRMS API health: ok\n"
    assert captured.err == ""


def test_health_command_reports_error(monkeypatch, capsys):
    def fake_fetch_json(_url: str):
        return 200, {"status": "degraded"}

    monkeypatch.setattr("trms_cli.cli.fetch_json", fake_fetch_json)

    exit_code = main(["health"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "Error: TRMS API health payload is not ready\n"
