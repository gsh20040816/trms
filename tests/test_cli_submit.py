import json

from trms_cli.cli import CLI_JSON_SCHEMA_VERSION, main
from trms_cli.token_store import save_token_session


def test_submit_command_uploads_local_file_from_stored_session(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    upload_path = tmp_path / "ticket.pdf"
    upload_path.write_bytes(b"%PDF-1.4 fake invoice")
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://example.com/api/",
        member_id="2250001",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )
    seen = {}

    def fake_post_multipart_json(url: str, *, headers=None, fields=None, files=None):
        seen["url"] = url
        seen["headers"] = headers
        seen["fields"] = fields
        seen["files"] = files
        return 201, {
            "status": "success",
            "items": [
                {
                    "id": "material-001",
                    "task_id": "task-123",
                    "submitter_id": "2250001",
                    "material_type": "invoice",
                    "original_filename": "ticket.pdf",
                    "status": "assigned",
                }
            ],
        }

    monkeypatch.setattr("trms_cli.cli.post_multipart_json", fake_post_multipart_json)

    exit_code = main(
        [
            "submit",
            "--task-id",
            "task-123",
            "--material-type",
            "invoice",
            str(upload_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert "stored-access-token" not in captured.out
    assert "stored-access-token" not in captured.err
    assert seen["url"] == "http://example.com/api/tasks/task-123/materials"
    assert seen["headers"] == {"Authorization": "Bearer stored-access-token"}
    assert seen["fields"] == {
        "submitter_id": "2250001",
        "channel": "cli",
        "material_type": "invoice",
    }
    assert len(seen["files"]) == 1
    assert seen["files"][0].filename == "ticket.pdf"
    assert seen["files"][0].content_type == "application/pdf"
    assert seen["files"][0].content == b"%PDF-1.4 fake invoice"
    assert captured.out == (
        "Uploaded material material-001 for task task-123 "
        "(ticket.pdf, recognition: pending)\n"
    )


def test_submit_command_reports_json(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    upload_path = tmp_path / "ticket.pdf"
    upload_path.write_bytes(b"%PDF-1.4 fake invoice")
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250002",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_post_multipart_json(url: str, *, headers=None, fields=None, files=None):
        assert url == "http://127.0.0.1:8000/api/tasks/task-456/materials"
        assert headers == {"Authorization": "Bearer stored-access-token"}
        assert fields == {
            "submitter_id": "2250002",
            "channel": "cli",
            "material_type": "payment_record",
        }
        assert len(files) == 1
        assert files[0].filename == "ticket.pdf"
        return 201, {
            "status": "success",
            "items": [
                {
                    "id": "material-002",
                    "task_id": "task-456",
                    "submitter_id": "2250002",
                    "material_type": "payment_record",
                    "original_filename": "ticket.pdf",
                    "status": "assigned",
                }
            ],
        }

    monkeypatch.setattr("trms_cli.cli.post_multipart_json", fake_post_multipart_json)

    exit_code = main(
        [
            "submit",
            "--task-id",
            "task-456",
            "--material-type",
            "payment_record",
            "--json",
            str(upload_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": True,
        "command": "submit",
        "data": {
            "base_url": "http://127.0.0.1:8000",
            "task_id": "task-456",
            "member_id": "2250002",
            "item": {
                "id": "material-002",
                "task_id": "task-456",
                "submitter_id": "2250002",
                "material_type": "payment_record",
                "original_filename": "ticket.pdf",
                "status": "assigned",
                "recognition_status": "pending",
            },
        },
    }


def test_submit_command_requires_existing_local_file(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250003",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    exit_code = main(
        [
            "submit",
            "--task-id",
            "task-789",
            "--material-type",
            "invoice",
            "--json",
            str(tmp_path / "missing.pdf"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": False,
        "command": "submit",
        "error": {
            "code": "local_file_not_found",
            "message": f"local file does not exist: {tmp_path / 'missing.pdf'}",
        },
    }


def test_submit_command_reports_backend_error_without_leaking_token(
    monkeypatch,
    tmp_path,
    capsys,
):
    config_dir = tmp_path / "config"
    upload_path = tmp_path / "ticket.pdf"
    upload_path.write_bytes(b"%PDF-1.4 fake invoice")
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250999",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_post_multipart_json(url: str, *, headers=None, fields=None, files=None):
        raise Exception("unexpected")

    def fake_post_error(url: str, *, headers=None, fields=None, files=None):
        from trms_cli.cli import CliError

        raise CliError(
            "request failed with status 409: submitter is not a member of the task: 2250999",
            code="http_error",
        )

    monkeypatch.setattr("trms_cli.cli.post_multipart_json", fake_post_error)

    exit_code = main(
        [
            "submit",
            "--task-id",
            "task-789",
            "--material-type",
            "invoice",
            str(upload_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "stored-access-token" not in captured.err
    assert captured.err == (
        "Error: request failed with status 409: "
        "submitter is not a member of the task: 2250999\n"
    )


def test_submit_command_reports_partial_success_for_batch_upload(
    monkeypatch,
    tmp_path,
    capsys,
):
    config_dir = tmp_path / "config"
    invoice_path = tmp_path / "ticket.pdf"
    note_path = tmp_path / "notes.txt"
    invoice_path.write_bytes(b"%PDF-1.4 fake invoice")
    note_path.write_text("plain-text", encoding="utf-8")
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250111",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )
    seen = {}

    def fake_post_multipart_json(url: str, *, headers=None, fields=None, files=None):
        seen["url"] = url
        seen["headers"] = headers
        seen["fields"] = fields
        seen["files"] = files
        return 207, {
            "status": "partial_success",
            "items": [
                {
                    "id": "material-101",
                    "task_id": "task-101",
                    "submitter_id": "2250111",
                    "material_type": "invoice",
                    "original_filename": "ticket.pdf",
                    "status": "assigned",
                }
            ],
            "failures": [
                {
                    "original_filename": "notes.txt",
                    "error_code": "unsupported_content_type",
                    "detail": "unsupported material content type: text/plain",
                }
            ],
        }

    monkeypatch.setattr("trms_cli.cli.post_multipart_json", fake_post_multipart_json)

    exit_code = main(
        [
            "submit",
            "--task-id",
            "task-101",
            "--material-type",
            "invoice",
            str(invoice_path),
            str(note_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err == ""
    assert seen["url"] == "http://127.0.0.1:8000/api/tasks/task-101/materials"
    assert seen["headers"] == {"Authorization": "Bearer stored-access-token"}
    assert seen["fields"] == {
        "submitter_id": "2250111",
        "channel": "cli",
        "material_type": "invoice",
    }
    assert [item.filename for item in seen["files"]] == ["ticket.pdf", "notes.txt"]
    assert captured.out == (
        "Submit result: partial_success (1 uploaded, 1 failed)\n"
        "OK\tticket.pdf\tmaterial-101\ttask-101\tpending\n"
        "FAIL\tnotes.txt\tunsupported_content_type\t"
        "unsupported material content type: text/plain\n"
    )


def test_submit_command_reports_failed_batch_result_as_json(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    first_path = tmp_path / "missing-name.pdf"
    second_path = tmp_path / "notes.txt"
    first_path.write_bytes(b"%PDF-1.4 fake invoice")
    second_path.write_text("plain-text", encoding="utf-8")
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250222",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_post_multipart_json(url: str, *, headers=None, fields=None, files=None):
        return 422, {
            "status": "failed",
            "items": [],
            "failures": [
                {
                    "original_filename": "   ",
                    "error_code": "missing_filename",
                    "detail": "uploaded file must have a filename",
                },
                {
                    "original_filename": "notes.txt",
                    "error_code": "unsupported_content_type",
                    "detail": "unsupported material content type: text/plain",
                },
            ],
        }

    monkeypatch.setattr("trms_cli.cli.post_multipart_json", fake_post_multipart_json)

    exit_code = main(
        [
            "submit",
            "--task-id",
            "task-202",
            "--material-type",
            "invoice",
            "--json",
            str(first_path),
            str(second_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": False,
        "command": "submit",
        "data": {
            "base_url": "http://127.0.0.1:8000",
            "task_id": "task-202",
            "member_id": "2250222",
            "status": "failed",
            "success_count": 0,
            "failure_count": 2,
            "items": [],
            "failures": [
                {
                    "original_filename": "   ",
                    "error_code": "missing_filename",
                    "detail": "uploaded file must have a filename",
                },
                {
                    "original_filename": "notes.txt",
                    "error_code": "unsupported_content_type",
                    "detail": "unsupported material content type: text/plain",
                },
            ],
        },
    }
