from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import getpass
import json
import mimetypes
import os
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from trms_backend.domain.materials import (
    MAX_MATERIAL_UPLOAD_SIZE_BYTES,
    SUPPORTED_MATERIAL_UPLOAD_CONTENT_TYPES,
)
from trms_cli.token_store import TokenStoreError, load_token_session, save_token_session

DEFAULT_BASE_URL = os.getenv("TRMS_API_BASE_URL", "http://127.0.0.1:8000")
CLI_JSON_SCHEMA_VERSION = "trms-cli.v1"
ACCESS_TOKEN_ENV = "TRMS_CLI_ACCESS_TOKEN"
REFRESH_TOKEN_ENV = "TRMS_CLI_REFRESH_TOKEN"


class CliError(Exception):
    """Raised when a CLI command cannot complete successfully."""

    def __init__(self, message: str, *, code: str = "cli_error") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class VisibleTaskSummary:
    id: str
    competition_name: str
    status: str
    deadline: str


@dataclass(frozen=True)
class MaterialUploadSummary:
    id: str
    task_id: str
    submitter_id: str
    material_type: str
    original_filename: str
    status: str
    recognition_status: str


@dataclass(frozen=True)
class MaterialUploadFailure:
    original_filename: str | None
    error_code: str
    detail: str


@dataclass(frozen=True)
class MaterialUploadBatchResult:
    status: str
    items: list[MaterialUploadSummary]
    failures: list[MaterialUploadFailure]


@dataclass(frozen=True)
class MultipartUploadFile:
    field_name: str
    filename: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class TaskStatusCounts:
    material_count: int
    missing_material_count: int
    expense_detail_count: int
    recognition_pending_count: int
    recognition_succeeded_count: int
    recognition_failed_count: int
    recognition_needs_confirmation_count: int
    validation_passed_count: int
    validation_failed_count: int
    validation_pending_count: int
    validation_not_applicable_count: int
    confirmed_expense_count: int
    pending_confirmation_count: int
    disputed_confirmation_count: int
    missing_confirmation_count: int


@dataclass(frozen=True)
class MemberMaterialStatus:
    material_id: str
    original_filename: str
    material_type: str
    material_status: str
    recognition_status: str | None
    validation_status: str
    invoice_id: str | None
    invoice_number: str | None
    validation_messages: list[str]


@dataclass(frozen=True)
class MissingMaterialStatus:
    invoice_id: str
    invoice_number: str
    required_material_type: str
    message: str


@dataclass(frozen=True)
class ExpenseConfirmationStatus:
    split_id: str
    invoice_id: str
    invoice_number: str
    amount_cents: int
    confirmation_status: str | None
    dispute_reason: str | None


@dataclass(frozen=True)
class TaskStatusReport:
    task_id: str
    actor_id: str
    total_expense_amount_cents: int
    counts: TaskStatusCounts
    materials: list[MemberMaterialStatus]
    missing_materials: list[MissingMaterialStatus]
    expense_details: list[ExpenseConfirmationStatus]


@dataclass(frozen=True)
class VisibleMissingMaterialReport:
    task_id: str
    actor_id: str
    scope: str
    items: list[MissingMaterialStatus]


EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_PARTIAL_SUCCESS = 2
LOCAL_BATCH_PRECHECK_ERROR_CODES = frozenset(
    {
        "local_empty_file",
        "local_file_too_large",
        "local_unsupported_content_type",
    }
)


def emit_json(payload: dict[str, object], *, stream: object | None = None) -> None:
    print(json.dumps(payload, ensure_ascii=False), file=stream or sys.stdout)


def fetch_json(url: str, *, headers: dict[str, str] | None = None) -> tuple[int, object]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    request = Request(url, method="GET", headers=request_headers)
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
            return response.status, payload
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        if detail:
            raise CliError(
                f"request failed with status {error.code}: {detail}",
                code="http_error",
            ) from error
        raise CliError(f"request failed with status {error.code}", code="http_error") from error
    except URLError as error:
        raise CliError(f"unable to reach TRMS API: {error.reason}", code="network_error") from error
    except json.JSONDecodeError as error:
        raise CliError("TRMS API returned invalid JSON", code="invalid_json_response") from error


def post_multipart_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    fields: dict[str, str],
    files: list[MultipartUploadFile],
) -> tuple[int, object]:
    body, content_type = encode_multipart_form_data(fields=fields, files=files)
    request_headers = {
        "Accept": "application/json",
        "Content-Type": content_type,
        "Content-Length": str(len(body)),
    }
    if headers:
        request_headers.update(headers)
    request = Request(url, method="POST", headers=request_headers, data=body)
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
            return response.status, payload
    except HTTPError as error:
        detail, payload = read_http_error_payload(error)
        if error.code == 422 and is_material_upload_failed_payload(payload):
            return error.code, payload
        if detail:
            raise CliError(
                f"request failed with status {error.code}: {detail}",
                code="http_error",
            ) from error
        raise CliError(f"request failed with status {error.code}", code="http_error") from error
    except URLError as error:
        raise CliError(f"unable to reach TRMS API: {error.reason}", code="network_error") from error
    except json.JSONDecodeError as error:
        raise CliError("TRMS API returned invalid JSON", code="invalid_json_response") from error


def read_http_error_payload(error: HTTPError) -> tuple[str | None, object | None]:
    payload = error.read().decode("utf-8", errors="replace").strip()
    if not payload:
        return None, None

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return payload, None

    if isinstance(parsed, dict):
        detail = parsed.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip(), parsed
    return payload, parsed


def is_material_upload_failed_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    return payload.get("status") == "failed" and isinstance(payload.get("failures"), list)


def encode_multipart_form_data(
    *,
    fields: dict[str, str],
    files: list[MultipartUploadFile],
) -> tuple[bytes, str]:
    boundary = f"trms-cli-{uuid4().hex}"
    body = bytearray()

    for field_name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'.encode("utf-8")
        )
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    for upload_file in files:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                'Content-Disposition: form-data; '
                f'name="{upload_file.field_name}"; filename="{upload_file.filename}"\r\n'
            ).encode("utf-8")
        )
        body.extend(f"Content-Type: {upload_file.content_type}\r\n\r\n".encode("utf-8"))
        body.extend(upload_file.content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trms-cli", description="TRMS command line client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser(
        "login",
        help="store pre-issued CLI access and refresh tokens",
    )
    login_parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="TRMS API base URL, defaults to TRMS_API_BASE_URL or http://127.0.0.1:8000",
    )
    login_parser.add_argument(
        "--member-id",
        required=True,
        help="bind the CLI session to a task member id",
    )
    login_parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="emit machine-readable JSON output",
    )
    login_parser.set_defaults(handler=run_login_command)

    health_parser = subparsers.add_parser("health", help="check TRMS API health")
    health_parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="TRMS API base URL, defaults to TRMS_API_BASE_URL or http://127.0.0.1:8000",
    )
    health_parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="emit machine-readable JSON output",
    )
    health_parser.set_defaults(handler=run_health_command)

    tasks_parser = subparsers.add_parser(
        "tasks",
        help="list current submission tasks from the stored CLI session",
    )
    tasks_parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="emit machine-readable JSON output",
    )
    tasks_parser.set_defaults(handler=run_tasks_command)

    submit_parser = subparsers.add_parser(
        "submit",
        help="upload one or more local material files to a visible reimbursement task",
    )
    submit_parser.add_argument(
        "--task-id",
        required=True,
        help="target reimbursement task id",
    )
    submit_parser.add_argument(
        "--material-type",
        required=True,
        help="material type such as invoice or payment_record",
    )
    submit_parser.add_argument(
        "file_paths",
        nargs="+",
        help="one or more local file paths to upload",
    )
    submit_parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="emit machine-readable JSON output",
    )
    submit_parser.set_defaults(handler=run_submit_command)

    status_parser = subparsers.add_parser(
        "status",
        help="show member-specific material, validation, missing-material and confirmation status",
    )
    status_parser.add_argument(
        "--task-id",
        required=True,
        help="target reimbursement task id",
    )
    status_parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="emit machine-readable JSON output",
    )
    status_parser.set_defaults(handler=run_status_command)

    missing_materials_parser = subparsers.add_parser(
        "missing-materials",
        help="show member-specific missing supporting materials for a reimbursement task",
    )
    missing_materials_parser.add_argument(
        "--task-id",
        required=True,
        help="target reimbursement task id",
    )
    missing_materials_parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="emit machine-readable JSON output",
    )
    missing_materials_parser.set_defaults(handler=run_missing_materials_command)

    return parser


def is_interactive_input() -> bool:
    return sys.stdin.isatty()


def load_secret(*, label: str, env_name: str) -> str:
    if env_value := os.getenv(env_name):
        secret = env_value.strip()
        if secret:
            return secret
        raise CliError(f"{env_name} is empty", code="login_token_missing")

    if not is_interactive_input():
        raise CliError(
            f"{env_name} is not set and CLI cannot prompt in non-interactive mode",
            code="login_token_missing",
        )

    secret = getpass.getpass(f"{label}: ").strip()
    if not secret:
        raise CliError(f"{label} is required", code="login_token_missing")
    return secret


def run_login_command(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    member_id = args.member_id.strip()
    if not member_id:
        raise CliError("member id is required", code="member_binding_required")
    access_token = load_secret(label="TRMS CLI access token", env_name=ACCESS_TOKEN_ENV)
    refresh_token = load_secret(label="TRMS CLI refresh token", env_name=REFRESH_TOKEN_ENV)

    try:
        token_store_path = save_token_session(
            base_url=base_url,
            member_id=member_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except TokenStoreError as error:
        raise CliError(str(error), code="token_store_error") from error

    if args.json_output:
        emit_json(
            {
                "schema_version": CLI_JSON_SCHEMA_VERSION,
                "ok": True,
                "command": "login",
                "data": {
                    "base_url": base_url,
                    "member_id": member_id,
                    "token_store_backend": "local_file",
                    "token_store_path": str(token_store_path),
                },
            }
        )
        return 0

    print(f"Stored TRMS CLI session for member {member_id} at {token_store_path}")
    return 0


def run_health_command(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    status_code, payload = fetch_json(f"{base_url}/health")
    if status_code != 200:
        raise CliError(
            f"health endpoint returned unexpected status {status_code}",
            code="health_unexpected_status",
        )
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise CliError("TRMS API health payload is not ready", code="health_not_ready")

    if args.json_output:
        emit_json(
            {
                "schema_version": CLI_JSON_SCHEMA_VERSION,
                "ok": True,
                "command": "health",
                "data": {
                    "status": "ok",
                    "base_url": base_url,
                },
            }
        )
        return 0

    print("TRMS API health: ok")
    return 0


def run_tasks_command(args: argparse.Namespace) -> int:
    try:
        session = load_token_session()
    except TokenStoreError as error:
        raise CliError(str(error), code="login_required") from error

    base_url = session.base_url.rstrip("/")
    status_code, payload = fetch_json(
        build_task_list_url(base_url, member_id=session.member_id),
        headers={"Authorization": f"Bearer {session.access_token}"},
    )
    if status_code != 200:
        raise CliError(
            f"task list endpoint returned unexpected status {status_code}",
            code="task_list_unexpected_status",
        )

    tasks = parse_visible_tasks(payload)
    if args.json_output:
        emit_json(
            {
                "schema_version": CLI_JSON_SCHEMA_VERSION,
                "ok": True,
                "command": "tasks",
                "data": {
                    "base_url": base_url,
                    "member_id": session.member_id,
                    "count": len(tasks),
                    "items": [asdict(task) for task in tasks],
                },
            }
        )
        return 0

    if not tasks:
        print("No current submission tasks.")
        return 0

    print("task_id\tcompetition_name\tstatus\tdeadline")
    for task in tasks:
        print(f"{task.id}\t{task.competition_name}\t{task.status}\t{task.deadline}")
    return 0


def run_submit_command(args: argparse.Namespace) -> int:
    try:
        session = load_token_session()
    except TokenStoreError as error:
        raise CliError(str(error), code="login_required") from error

    upload_files, local_failures = prepare_upload_files(args.file_paths)
    base_url = session.base_url.rstrip("/")
    result = build_local_only_submit_result(local_failures)
    if upload_files:
        status_code, payload = post_multipart_json(
            build_material_submit_url(base_url, task_id=args.task_id),
            headers={"Authorization": f"Bearer {session.access_token}"},
            fields={
                "submitter_id": session.member_id,
                "channel": "cli",
                "material_type": args.material_type,
            },
            files=upload_files,
        )
        if status_code not in {201, 207, 422}:
            raise CliError(
                f"material submit endpoint returned unexpected status {status_code}",
                code="material_submit_unexpected_status",
            )

        result = merge_material_upload_batch_results(
            parse_material_upload_batch_result(payload),
            local_failures=local_failures,
        )

    exit_code = material_submit_exit_code(result)
    if args.json_output:
        emit_submit_json_result(
            base_url=base_url,
            requested_task_id=args.task_id,
            member_id=session.member_id,
            result=result,
        )
        return exit_code

    emit_submit_text_result(result)
    return exit_code


def run_status_command(args: argparse.Namespace) -> int:
    try:
        session = load_token_session()
    except TokenStoreError as error:
        raise CliError(str(error), code="login_required") from error

    base_url = session.base_url.rstrip("/")
    status_code, payload = fetch_json(
        build_task_status_url(base_url, task_id=args.task_id, actor_id=session.member_id),
        headers={"Authorization": f"Bearer {session.access_token}"},
    )
    if status_code != 200:
        raise CliError(
            f"task member status endpoint returned unexpected status {status_code}",
            code="task_status_unexpected_status",
        )

    report = parse_task_status_report(payload)
    if args.json_output:
        emit_json(
            {
                "schema_version": CLI_JSON_SCHEMA_VERSION,
                "ok": True,
                "command": "status",
                "data": {
                    "base_url": base_url,
                    "task_id": report.task_id,
                    "member_id": report.actor_id,
                    "total_expense_amount_cents": report.total_expense_amount_cents,
                    "counts": asdict(report.counts),
                    "materials": [asdict(item) for item in report.materials],
                    "missing_materials": [asdict(item) for item in report.missing_materials],
                    "expense_details": [asdict(item) for item in report.expense_details],
                },
            }
        )
        return 0

    emit_status_text_result(report)
    return 0


def run_missing_materials_command(args: argparse.Namespace) -> int:
    try:
        session = load_token_session()
    except TokenStoreError as error:
        raise CliError(str(error), code="login_required") from error

    base_url = session.base_url.rstrip("/")
    status_code, payload = fetch_json(
        build_task_missing_materials_url(base_url, task_id=args.task_id, actor_id=session.member_id),
        headers={"Authorization": f"Bearer {session.access_token}"},
    )
    if status_code != 200:
        raise CliError(
            f"task missing materials endpoint returned unexpected status {status_code}",
            code="missing_materials_unexpected_status",
        )

    report = parse_visible_missing_material_report(payload)
    if args.json_output:
        emit_json(
            {
                "schema_version": CLI_JSON_SCHEMA_VERSION,
                "ok": True,
                "command": "missing-materials",
                "data": {
                    "base_url": base_url,
                    "task_id": report.task_id,
                    "member_id": report.actor_id,
                    "scope": report.scope,
                    "count": len(report.items),
                    "items": [asdict(item) for item in report.items],
                },
            }
        )
        return 0

    emit_missing_materials_text_result(report)
    return 0


def build_task_list_url(base_url: str, *, member_id: str) -> str:
    normalized_base_url = base_url.rstrip("/")
    query_string = urlencode({"member_id": member_id})
    if normalized_base_url.endswith("/api"):
        return f"{normalized_base_url}/tasks?{query_string}"
    return f"{normalized_base_url}/api/tasks?{query_string}"


def build_material_submit_url(base_url: str, *, task_id: str) -> str:
    normalized_base_url = base_url.rstrip("/")
    normalized_task_id = task_id.strip()
    if not normalized_task_id:
        raise CliError("task id is required", code="task_id_required")
    if normalized_base_url.endswith("/api"):
        return f"{normalized_base_url}/tasks/{normalized_task_id}/materials"
    return f"{normalized_base_url}/api/tasks/{normalized_task_id}/materials"


def build_task_status_url(base_url: str, *, task_id: str, actor_id: str) -> str:
    normalized_base_url = base_url.rstrip("/")
    normalized_task_id = task_id.strip()
    normalized_actor_id = actor_id.strip()
    if not normalized_task_id:
        raise CliError("task id is required", code="task_id_required")
    if not normalized_actor_id:
        raise CliError("member id is required", code="member_binding_required")
    query_string = urlencode({"actor_id": normalized_actor_id})
    if normalized_base_url.endswith("/api"):
        return f"{normalized_base_url}/tasks/{normalized_task_id}/member-status?{query_string}"
    return f"{normalized_base_url}/api/tasks/{normalized_task_id}/member-status?{query_string}"


def build_task_missing_materials_url(base_url: str, *, task_id: str, actor_id: str) -> str:
    normalized_base_url = base_url.rstrip("/")
    normalized_task_id = task_id.strip()
    normalized_actor_id = actor_id.strip()
    if not normalized_task_id:
        raise CliError("task id is required", code="task_id_required")
    if not normalized_actor_id:
        raise CliError("member id is required", code="member_binding_required")
    query_string = urlencode({"actor_id": normalized_actor_id})
    if normalized_base_url.endswith("/api"):
        return f"{normalized_base_url}/tasks/{normalized_task_id}/missing-materials?{query_string}"
    return f"{normalized_base_url}/api/tasks/{normalized_task_id}/missing-materials?{query_string}"


def prepare_upload_files(
    file_paths: list[str],
) -> tuple[list[MultipartUploadFile], list[MaterialUploadFailure]]:
    upload_files: list[MultipartUploadFile] = []
    local_failures: list[MaterialUploadFailure] = []
    for file_path in file_paths:
        try:
            upload_files.append(load_upload_file(file_path))
        except CliError as error:
            if error.code not in LOCAL_BATCH_PRECHECK_ERROR_CODES:
                raise
            path = Path(file_path).expanduser()
            local_failures.append(
                MaterialUploadFailure(
                    original_filename=path.name or None,
                    error_code=error.code,
                    detail=str(error),
                )
            )
    return upload_files, local_failures


def load_upload_file(file_path: str) -> MultipartUploadFile:
    path = Path(file_path).expanduser()
    if not path.exists():
        raise CliError(f"local file does not exist: {path}", code="local_file_not_found")
    if not path.is_file():
        raise CliError(f"upload path is not a file: {path}", code="local_file_invalid")

    try:
        content = path.read_bytes()
    except OSError as error:
        raise CliError(f"unable to read local file: {path}", code="local_file_unreadable") from error

    size_bytes = len(content)
    if size_bytes == 0:
        raise CliError(f"local file is empty: {path}", code="local_empty_file")
    if size_bytes > MAX_MATERIAL_UPLOAD_SIZE_BYTES:
        raise CliError(
            "local file exceeds size limit: "
            f"{path} ({size_bytes} bytes > {MAX_MATERIAL_UPLOAD_SIZE_BYTES} bytes)",
            code="local_file_too_large",
        )

    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    normalized_content_type = normalize_content_type(content_type)
    if normalized_content_type not in SUPPORTED_MATERIAL_UPLOAD_CONTENT_TYPES:
        supported = ", ".join(SUPPORTED_MATERIAL_UPLOAD_CONTENT_TYPES)
        raise CliError(
            "local file has unsupported content type: "
            f"{path} ({content_type}); supported content types: {supported}",
            code="local_unsupported_content_type",
        )

    return MultipartUploadFile(
        field_name="files",
        filename=path.name,
        content_type=content_type,
        content=content,
    )


def normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", maxsplit=1)[0].strip().lower()


def parse_material_upload_batch_result(payload: object) -> MaterialUploadBatchResult:
    if not isinstance(payload, dict):
        raise CliError(
            "TRMS API returned invalid material upload payload",
            code="material_submit_invalid_response",
        )

    items = payload.get("items")
    if not isinstance(items, list):
        raise CliError(
            "TRMS API returned invalid material upload payload",
            code="material_submit_invalid_response",
        )

    status = payload.get("status")
    if status not in {"success", "partial_success", "failed"}:
        raise CliError(
            "TRMS API returned invalid material upload payload",
            code="material_submit_invalid_response",
        )

    failures = payload.get("failures", [])
    if failures is None:
        failures = []
    if not isinstance(failures, list):
        raise CliError(
            "TRMS API returned invalid material upload payload",
            code="material_submit_invalid_response",
        )

    return MaterialUploadBatchResult(
        status=status,
        items=[parse_material_upload_summary(item) for item in items],
        failures=[parse_material_upload_failure(item) for item in failures],
    )


def parse_material_upload_summary(item: object) -> MaterialUploadSummary:
    if not isinstance(item, dict):
        raise CliError(
            "TRMS API returned invalid material upload payload",
            code="material_submit_invalid_response",
        )

    return MaterialUploadSummary(
        id=_require_non_empty_material_field(item, "id"),
        task_id=_require_non_empty_material_field(item, "task_id"),
        submitter_id=_require_non_empty_material_field(item, "submitter_id"),
        material_type=_require_non_empty_material_field(item, "material_type"),
        original_filename=_require_non_empty_material_field(item, "original_filename"),
        status=_require_non_empty_material_field(item, "status"),
        recognition_status="pending",
    )


def parse_material_upload_failure(item: object) -> MaterialUploadFailure:
    if not isinstance(item, dict):
        raise CliError(
            "TRMS API returned invalid material upload payload",
            code="material_submit_invalid_response",
        )

    original_filename = item.get("original_filename")
    if original_filename is not None and not isinstance(original_filename, str):
        raise CliError(
            "TRMS API returned invalid material upload payload",
            code="material_submit_invalid_response",
        )

    return MaterialUploadFailure(
        original_filename=original_filename,
        error_code=_require_non_empty_material_field(item, "error_code"),
        detail=_require_non_empty_material_field(item, "detail"),
    )


def material_submit_exit_code(result: MaterialUploadBatchResult) -> int:
    if result.status == "success":
        return EXIT_SUCCESS
    if result.status == "partial_success":
        return EXIT_PARTIAL_SUCCESS
    return EXIT_FAILURE


def build_local_only_submit_result(
    local_failures: list[MaterialUploadFailure],
) -> MaterialUploadBatchResult:
    if not local_failures:
        return MaterialUploadBatchResult(status="success", items=[], failures=[])
    return MaterialUploadBatchResult(status="failed", items=[], failures=local_failures)


def merge_material_upload_batch_results(
    result: MaterialUploadBatchResult,
    *,
    local_failures: list[MaterialUploadFailure],
) -> MaterialUploadBatchResult:
    if not local_failures:
        return result

    failures = [*result.failures, *local_failures]
    if result.items:
        status = "partial_success"
    else:
        status = "failed"
    return MaterialUploadBatchResult(status=status, items=result.items, failures=failures)


def emit_submit_json_result(
    *,
    base_url: str,
    requested_task_id: str,
    member_id: str,
    result: MaterialUploadBatchResult,
) -> None:
    if is_single_success_result(result):
        emit_json(
            {
                "schema_version": CLI_JSON_SCHEMA_VERSION,
                "ok": True,
                "command": "submit",
                "data": {
                    "base_url": base_url,
                    "task_id": result.items[0].task_id,
                    "member_id": member_id,
                    "item": asdict(result.items[0]),
                },
            }
        )
        return

    emit_json(
        {
            "schema_version": CLI_JSON_SCHEMA_VERSION,
            "ok": result.status == "success",
            "command": "submit",
            "data": {
                "base_url": base_url,
                "task_id": requested_task_id,
                "member_id": member_id,
                "status": result.status,
                "success_count": len(result.items),
                "failure_count": len(result.failures),
                "items": [asdict(item) for item in result.items],
                "failures": [asdict(item) for item in result.failures],
            },
        }
    )


def emit_submit_text_result(result: MaterialUploadBatchResult) -> None:
    if is_single_success_result(result):
        upload = result.items[0]
        print(
            "Uploaded material "
            f"{upload.id} for task {upload.task_id} "
            f"({upload.original_filename}, recognition: {upload.recognition_status})"
        )
        return

    print(
        "Submit result: "
        f"{result.status} ({len(result.items)} uploaded, {len(result.failures)} failed)"
    )
    for item in result.items:
        print(
            "OK\t"
            f"{item.original_filename}\t{item.id}\t{item.task_id}\t{item.recognition_status}"
        )
    for failure in result.failures:
        filename = failure.original_filename or "<unknown>"
        print(f"FAIL\t{filename}\t{failure.error_code}\t{failure.detail}")


def is_single_success_result(result: MaterialUploadBatchResult) -> bool:
    return result.status == "success" and len(result.items) == 1 and not result.failures


def _require_non_empty_material_field(item: dict[str, object], field_name: str) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise CliError(
            f"TRMS API material upload payload is missing a valid {field_name!r} field",
            code="material_submit_invalid_response",
        )
    return value.strip()


def parse_visible_tasks(payload: object) -> list[VisibleTaskSummary]:
    if not isinstance(payload, list):
        raise CliError("TRMS API returned invalid task list payload", code="task_list_invalid_response")

    visible_tasks: list[VisibleTaskSummary] = []
    now = datetime.now(timezone.utc)
    for item in payload:
        if not isinstance(item, dict):
            raise CliError(
                "TRMS API returned invalid task list payload", code="task_list_invalid_response"
            )

        task_id = _require_non_empty_task_field(item, "id")
        competition_name = _require_non_empty_task_field(item, "competition_name")
        status = _require_non_empty_task_field(item, "status")
        deadline = _require_non_empty_task_field(item, "deadline")
        if status != "open":
            continue

        if parse_task_deadline(deadline) <= now:
            continue

        visible_tasks.append(
            VisibleTaskSummary(
                id=task_id,
                competition_name=competition_name,
                status=status,
                deadline=deadline,
            )
        )

    return visible_tasks


def parse_task_status_report(payload: object) -> TaskStatusReport:
    if not isinstance(payload, dict):
        raise CliError("TRMS API returned invalid task status payload", code="task_status_invalid_response")

    materials = payload.get("materials")
    missing_materials = payload.get("missing_materials")
    expense_details = payload.get("expense_details")
    counts = payload.get("counts")
    if not isinstance(materials, list) or not isinstance(missing_materials, list):
        raise CliError("TRMS API returned invalid task status payload", code="task_status_invalid_response")
    if not isinstance(expense_details, list) or not isinstance(counts, dict):
        raise CliError("TRMS API returned invalid task status payload", code="task_status_invalid_response")

    return TaskStatusReport(
        task_id=_require_non_empty_status_field(payload, "task_id"),
        actor_id=_require_non_empty_status_field(payload, "actor_id"),
        total_expense_amount_cents=_require_int_status_field(payload, "total_expense_amount_cents"),
        counts=parse_task_status_counts(counts),
        materials=[parse_member_material_status(item) for item in materials],
        missing_materials=[parse_missing_material_status(item) for item in missing_materials],
        expense_details=[parse_expense_confirmation_status(item) for item in expense_details],
    )


def parse_visible_missing_material_report(payload: object) -> VisibleMissingMaterialReport:
    if not isinstance(payload, dict):
        raise CliError(
            "TRMS API returned invalid missing materials payload",
            code="missing_materials_invalid_response",
        )

    items = payload.get("items")
    if not isinstance(items, list):
        raise CliError(
            "TRMS API returned invalid missing materials payload",
            code="missing_materials_invalid_response",
        )

    scope = payload.get("scope")
    if scope not in {"task", "member"}:
        raise CliError(
            "TRMS API returned invalid missing materials payload",
            code="missing_materials_invalid_response",
        )

    return VisibleMissingMaterialReport(
        task_id=_require_non_empty_missing_material_field(payload, "task_id"),
        actor_id=_require_non_empty_missing_material_field(payload, "actor_id"),
        scope=scope,
        items=[parse_missing_material_item(item) for item in items],
    )


def parse_task_status_counts(payload: dict[str, object]) -> TaskStatusCounts:
    return TaskStatusCounts(
        material_count=_require_int_status_field(payload, "material_count"),
        missing_material_count=_require_int_status_field(payload, "missing_material_count"),
        expense_detail_count=_require_int_status_field(payload, "expense_detail_count"),
        recognition_pending_count=_require_int_status_field(payload, "recognition_pending_count"),
        recognition_succeeded_count=_require_int_status_field(payload, "recognition_succeeded_count"),
        recognition_failed_count=_require_int_status_field(payload, "recognition_failed_count"),
        recognition_needs_confirmation_count=_require_int_status_field(
            payload, "recognition_needs_confirmation_count"
        ),
        validation_passed_count=_require_int_status_field(payload, "validation_passed_count"),
        validation_failed_count=_require_int_status_field(payload, "validation_failed_count"),
        validation_pending_count=_require_int_status_field(payload, "validation_pending_count"),
        validation_not_applicable_count=_require_int_status_field(
            payload, "validation_not_applicable_count"
        ),
        confirmed_expense_count=_require_int_status_field(payload, "confirmed_expense_count"),
        pending_confirmation_count=_require_int_status_field(payload, "pending_confirmation_count"),
        disputed_confirmation_count=_require_int_status_field(payload, "disputed_confirmation_count"),
        missing_confirmation_count=_require_int_status_field(payload, "missing_confirmation_count"),
    )


def parse_member_material_status(item: object) -> MemberMaterialStatus:
    if not isinstance(item, dict):
        raise CliError("TRMS API returned invalid task status payload", code="task_status_invalid_response")
    validation_messages = item.get("validation_messages", [])
    if not isinstance(validation_messages, list) or any(
        not isinstance(message, str) for message in validation_messages
    ):
        raise CliError("TRMS API returned invalid task status payload", code="task_status_invalid_response")

    return MemberMaterialStatus(
        material_id=_require_non_empty_status_field(item, "material_id"),
        original_filename=_require_non_empty_status_field(item, "original_filename"),
        material_type=_require_non_empty_status_field(item, "material_type"),
        material_status=_require_non_empty_status_field(item, "material_status"),
        recognition_status=_optional_status_string(item, "recognition_status"),
        validation_status=_require_non_empty_status_field(item, "validation_status"),
        invoice_id=_optional_status_string(item, "invoice_id"),
        invoice_number=_optional_status_string(item, "invoice_number"),
        validation_messages=validation_messages,
    )


def parse_missing_material_status(item: object) -> MissingMaterialStatus:
    return parse_missing_material_item(item)


def parse_missing_material_item(item: object) -> MissingMaterialStatus:
    if not isinstance(item, dict):
        raise CliError(
            "TRMS API returned invalid missing materials payload",
            code="missing_materials_invalid_response",
        )
    return MissingMaterialStatus(
        invoice_id=_require_non_empty_missing_material_field(item, "invoice_id"),
        invoice_number=_require_non_empty_missing_material_field(item, "invoice_number"),
        required_material_type=_require_non_empty_missing_material_field(item, "required_material_type"),
        message=_require_non_empty_missing_material_field(item, "message"),
    )


def parse_expense_confirmation_status(item: object) -> ExpenseConfirmationStatus:
    if not isinstance(item, dict):
        raise CliError("TRMS API returned invalid task status payload", code="task_status_invalid_response")
    invoice = item.get("invoice")
    if not isinstance(invoice, dict):
        raise CliError("TRMS API returned invalid task status payload", code="task_status_invalid_response")
    confirmation = item.get("confirmation")
    if confirmation is not None and not isinstance(confirmation, dict):
        raise CliError("TRMS API returned invalid task status payload", code="task_status_invalid_response")

    return ExpenseConfirmationStatus(
        split_id=_require_non_empty_status_field(item, "split_id"),
        invoice_id=_require_non_empty_status_field(invoice, "id"),
        invoice_number=_require_non_empty_status_field(invoice, "invoice_number"),
        amount_cents=_require_int_status_field(item, "amount_cents"),
        confirmation_status=(
            _require_non_empty_status_field(confirmation, "status") if confirmation is not None else None
        ),
        dispute_reason=(
            _optional_status_string(confirmation, "dispute_reason") if confirmation is not None else None
        ),
    )


def emit_status_text_result(report: TaskStatusReport) -> None:
    print(f"Task status for task {report.task_id} member {report.actor_id}")
    print(f"Materials: {report.counts.material_count}")
    if report.materials:
        print("material_id\tfilename\ttype\trecognition\tvalidation\tinvoice_number")
        for item in report.materials:
            print(
                f"{item.material_id}\t{item.original_filename}\t{item.material_type}\t"
                f"{item.recognition_status or 'missing'}\t{item.validation_status}\t"
                f"{item.invoice_number or ''}"
            )
    else:
        print("No related materials found.")

    print(f"Missing materials: {report.counts.missing_material_count}")
    if report.missing_materials:
        print("invoice_number\trequired_material_type\tmessage")
        for item in report.missing_materials:
            print(f"{item.invoice_number}\t{item.required_material_type}\t{item.message}")
    else:
        print("No missing materials.")

    print(
        "Expense confirmations: "
        f"{report.counts.expense_detail_count} (total {report.total_expense_amount_cents} cents)"
    )
    if report.expense_details:
        print("split_id\tinvoice_number\tamount_cents\tconfirmation_status")
        for item in report.expense_details:
            print(
                f"{item.split_id}\t{item.invoice_number}\t{item.amount_cents}\t"
                f"{item.confirmation_status or 'missing'}"
            )
    else:
        print("No related expense details.")


def emit_missing_materials_text_result(report: VisibleMissingMaterialReport) -> None:
    print(f"Missing materials for task {report.task_id} member {report.actor_id}")
    print(f"Count: {len(report.items)}")
    if report.items:
        print("invoice_number\trequired_material_type\tmessage")
        for item in report.items:
            print(f"{item.invoice_number}\t{item.required_material_type}\t{item.message}")
        return

    print("No missing materials.")


def _require_non_empty_task_field(item: dict[str, object], field_name: str) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise CliError(
            f"TRMS API task payload is missing a valid {field_name!r} field",
            code="task_list_invalid_response",
        )
    return value.strip()


def _require_non_empty_status_field(item: dict[str, object], field_name: str) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise CliError(
            f"TRMS API task status payload is missing a valid {field_name!r} field",
            code="task_status_invalid_response",
        )
    return value.strip()


def _optional_status_string(item: dict[str, object], field_name: str) -> str | None:
    value = item.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CliError("TRMS API returned invalid task status payload", code="task_status_invalid_response")
    normalized = value.strip()
    return normalized or None


def _require_non_empty_missing_material_field(item: dict[str, object], field_name: str) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise CliError(
            f"TRMS API missing materials payload is missing a valid {field_name!r} field",
            code="missing_materials_invalid_response",
        )
    return value.strip()


def _require_int_status_field(item: dict[str, object], field_name: str) -> int:
    value = item.get(field_name)
    if not isinstance(value, int):
        raise CliError(
            f"TRMS API task status payload is missing a valid {field_name!r} field",
            code="task_status_invalid_response",
        )
    return value


def parse_task_deadline(value: str) -> datetime:
    normalized_value = value
    if normalized_value.endswith("Z"):
        normalized_value = f"{normalized_value[:-1]}+00:00"

    try:
        deadline = datetime.fromisoformat(normalized_value)
    except ValueError as error:
        raise CliError(
            f"TRMS API returned an invalid task deadline: {value}",
            code="task_list_invalid_response",
        ) from error

    if deadline.tzinfo is None:
        return deadline.replace(tzinfo=timezone.utc)
    return deadline


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.handler(args)
    except CliError as error:
        if getattr(args, "json_output", False):
            emit_json(
                {
                    "schema_version": CLI_JSON_SCHEMA_VERSION,
                    "ok": False,
                    "command": getattr(args, "command", None),
                    "error": {
                        "code": error.code,
                        "message": str(error),
                    },
                },
                stream=sys.stderr,
            )
            return 1

        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
