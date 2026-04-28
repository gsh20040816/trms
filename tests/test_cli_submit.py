import json
import pytest

from trms_backend.domain.materials import MAX_MATERIAL_UPLOAD_SIZE_BYTES
from trms_cli.cli import CLI_JSON_SCHEMA_VERSION, build_cli_request_headers, main
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
    assert seen["headers"] == build_cli_request_headers(access_token="stored-access-token")
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
        assert headers == build_cli_request_headers(access_token="stored-access-token")
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


def test_submit_command_reports_local_validation_failure_without_upload(
    monkeypatch,
    tmp_path,
    capsys,
):
    config_dir = tmp_path / "config"
    upload_path = tmp_path / "notes.txt"
    upload_path.write_text("plain-text", encoding="utf-8")
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250100",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_post_multipart_json(url: str, *, headers=None, fields=None, files=None):
        raise AssertionError("local precheck failure should not trigger upload")

    monkeypatch.setattr("trms_cli.cli.post_multipart_json", fake_post_multipart_json)

    exit_code = main(
        [
            "submit",
            "--task-id",
            "task-100",
            "--material-type",
            "invoice",
            "--json",
            str(upload_path),
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
            "task_id": "task-100",
            "member_id": "2250100",
            "status": "failed",
            "success_count": 0,
            "failure_count": 1,
            "items": [],
            "failures": [
                {
                    "original_filename": "notes.txt",
                    "error_code": "local_unsupported_content_type",
                    "detail": (
                        "local file has unsupported content type: "
                        f"{upload_path} (text/plain); supported content types: "
                        "application/pdf, application/zip, image/jpeg, image/png, image/webp"
                    ),
                }
            ],
        },
    }


def test_submit_command_reports_local_oversized_file_without_upload(
    monkeypatch,
    tmp_path,
    capsys,
):
    config_dir = tmp_path / "config"
    upload_path = tmp_path / "oversized.pdf"
    upload_path.write_bytes(b"x" * (MAX_MATERIAL_UPLOAD_SIZE_BYTES + 1))
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250101",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_post_multipart_json(url: str, *, headers=None, fields=None, files=None):
        raise AssertionError("oversized local file should not trigger upload")

    monkeypatch.setattr("trms_cli.cli.post_multipart_json", fake_post_multipart_json)

    exit_code = main(
        [
            "submit",
            "--task-id",
            "task-101",
            "--material-type",
            "invoice",
            str(upload_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == ""
    assert captured.out == (
        "Submit result: failed (0 uploaded, 1 failed)\n"
        "FAIL\toversized.pdf\tlocal_file_too_large\t"
        f"local file exceeds size limit: {upload_path} "
        f"({MAX_MATERIAL_UPLOAD_SIZE_BYTES + 1} bytes > "
        f"{MAX_MATERIAL_UPLOAD_SIZE_BYTES} bytes)\n"
    )


def test_submit_command_reports_partial_success_for_batch_upload_with_local_precheck_failure(
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
        return 201, {
            "status": "success",
            "items": [
                {
                    "id": "material-101",
                    "task_id": "task-101",
                    "submitter_id": "2250111",
                    "material_type": "invoice",
                    "original_filename": "ticket.pdf",
                    "status": "assigned",
                }
            ]
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
    assert seen["headers"] == build_cli_request_headers(access_token="stored-access-token")
    assert seen["fields"] == {
        "submitter_id": "2250111",
        "channel": "cli",
        "material_type": "invoice",
    }
    assert [item.filename for item in seen["files"]] == ["ticket.pdf"]
    assert captured.out == (
        "Submit result: partial_success (1 uploaded, 1 failed)\n"
        "OK\tticket.pdf\tmaterial-101\ttask-101\tpending\n"
        "FAIL\tnotes.txt\tlocal_unsupported_content_type\t"
        f"local file has unsupported content type: {note_path} "
        "(text/plain); supported content types: "
        "application/pdf, application/zip, image/jpeg, image/png, image/webp\n"
    )


def test_submit_command_reports_failed_batch_result_as_json(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    first_path = tmp_path / "first.pdf"
    second_path = tmp_path / "second.pdf"
    first_path.write_bytes(b"%PDF-1.4 fake invoice")
    second_path.write_bytes(b"%PDF-1.4 another fake invoice")
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
                    "original_filename": "first.pdf",
                    "error_code": "storage_error",
                    "detail": "failed to persist uploaded file: first.pdf",
                },
                {
                    "original_filename": "second.pdf",
                    "error_code": "storage_error",
                    "detail": "failed to persist uploaded file: second.pdf",
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
                    "original_filename": "first.pdf",
                    "error_code": "storage_error",
                    "detail": "failed to persist uploaded file: first.pdf",
                },
                {
                    "original_filename": "second.pdf",
                    "error_code": "storage_error",
                    "detail": "failed to persist uploaded file: second.pdf",
                },
            ],
        },
    }


def test_submit_command_recursively_expands_directory_without_following_symlinks(
    monkeypatch,
    tmp_path,
    capsys,
):
    config_dir = tmp_path / "config"
    upload_dir = tmp_path / "materials"
    nested_dir = upload_dir / "a-nested"
    nested_dir.mkdir(parents=True)
    (upload_dir / "b-invoice.pdf").write_bytes(b"%PDF-1.4 root invoice")
    (upload_dir / "z-payment.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (nested_dir / "a-ticket.pdf").write_bytes(b"%PDF-1.4 nested invoice")
    (nested_dir / "notes.txt").write_text("plain-text", encoding="utf-8")
    symlink_path = upload_dir / "linked-materials"
    try:
        symlink_path.symlink_to(nested_dir, target_is_directory=True)
    except OSError:
        pytest.skip("current filesystem does not support directory symlinks")

    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250333",
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
                    "id": "material-301",
                    "task_id": "task-303",
                    "submitter_id": "2250333",
                    "material_type": "invoice",
                    "original_filename": "a-ticket.pdf",
                    "status": "assigned",
                },
                {
                    "id": "material-302",
                    "task_id": "task-303",
                    "submitter_id": "2250333",
                    "material_type": "invoice",
                    "original_filename": "b-invoice.pdf",
                    "status": "assigned",
                },
                {
                    "id": "material-303",
                    "task_id": "task-303",
                    "submitter_id": "2250333",
                    "material_type": "invoice",
                    "original_filename": "z-payment.png",
                    "status": "assigned",
                },
            ],
        }

    monkeypatch.setattr("trms_cli.cli.post_multipart_json", fake_post_multipart_json)

    exit_code = main(
        [
            "submit",
            "--task-id",
            "task-303",
            "--material-type",
            "invoice",
            "--json",
            str(upload_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err == ""
    assert seen["url"] == "http://127.0.0.1:8000/api/tasks/task-303/materials"
    assert seen["headers"] == build_cli_request_headers(access_token="stored-access-token")
    assert seen["fields"] == {
        "submitter_id": "2250333",
        "channel": "cli",
        "material_type": "invoice",
    }
    assert [item.filename for item in seen["files"]] == [
        "a-ticket.pdf",
        "b-invoice.pdf",
        "z-payment.png",
    ]
    assert json.loads(captured.out) == {
        "schema_version": CLI_JSON_SCHEMA_VERSION,
        "ok": False,
        "command": "submit",
        "data": {
            "base_url": "http://127.0.0.1:8000",
            "task_id": "task-303",
            "member_id": "2250333",
            "status": "partial_success",
            "success_count": 3,
            "failure_count": 2,
            "items": [
                {
                    "id": "material-301",
                    "task_id": "task-303",
                    "submitter_id": "2250333",
                    "material_type": "invoice",
                    "original_filename": "a-ticket.pdf",
                    "status": "assigned",
                    "recognition_status": "pending",
                },
                {
                    "id": "material-302",
                    "task_id": "task-303",
                    "submitter_id": "2250333",
                    "material_type": "invoice",
                    "original_filename": "b-invoice.pdf",
                    "status": "assigned",
                    "recognition_status": "pending",
                },
                {
                    "id": "material-303",
                    "task_id": "task-303",
                    "submitter_id": "2250333",
                    "material_type": "invoice",
                    "original_filename": "z-payment.png",
                    "status": "assigned",
                    "recognition_status": "pending",
                },
            ],
            "failures": [
                {
                    "original_filename": "notes.txt",
                    "error_code": "local_unsupported_content_type",
                    "detail": (
                        "local file has unsupported content type: "
                        f"{nested_dir / 'notes.txt'} (text/plain); supported content types: "
                        "application/pdf, application/zip, image/jpeg, image/png, image/webp"
                    ),
                },
                {
                    "original_filename": "linked-materials",
                    "error_code": "local_symlink_not_supported",
                    "detail": (
                        "symbolic links are not supported during recursive upload: "
                        f"{symlink_path}"
                    ),
                },
            ],
        },
    }


def test_submit_command_reports_empty_directory_as_local_failure(
    monkeypatch,
    tmp_path,
    capsys,
):
    config_dir = tmp_path / "config"
    upload_dir = tmp_path / "empty-materials"
    upload_dir.mkdir()
    monkeypatch.setenv("TRMS_CLI_CONFIG_DIR", str(config_dir))
    save_token_session(
        base_url="http://127.0.0.1:8000",
        member_id="2250444",
        access_token="stored-access-token",
        refresh_token="stored-refresh-token",
    )

    def fake_post_multipart_json(url: str, *, headers=None, fields=None, files=None):
        raise AssertionError("empty directory should not trigger upload")

    monkeypatch.setattr("trms_cli.cli.post_multipart_json", fake_post_multipart_json)

    exit_code = main(
        [
            "submit",
            "--task-id",
            "task-404",
            "--material-type",
            "invoice",
            str(upload_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == ""
    assert captured.out == (
        "Submit result: failed (0 uploaded, 1 failed)\n"
        "FAIL\tempty-materials\tlocal_directory_empty\t"
        f"directory does not contain any uploadable files: {upload_dir}\n"
    )
