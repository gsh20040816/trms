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


def _require_non_empty_task_field(item: dict[str, object], field_name: str) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise CliError(
            f"TRMS API task payload is missing a valid {field_name!r} field",
            code="task_list_invalid_response",
        )
    return value.strip()


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
