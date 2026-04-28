from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import getpass
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
    access_token = load_secret(label="TRMS CLI access token", env_name=ACCESS_TOKEN_ENV)
    refresh_token = load_secret(label="TRMS CLI refresh token", env_name=REFRESH_TOKEN_ENV)

    try:
        token_store_path = save_token_session(
            base_url=base_url,
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
                    "token_store_backend": "local_file",
                    "token_store_path": str(token_store_path),
                },
            }
        )
        return 0

    print(f"Stored TRMS CLI tokens at {token_store_path}")
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
        build_task_list_url(base_url),
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


def build_task_list_url(base_url: str) -> str:
    normalized_base_url = base_url.rstrip("/")
    if normalized_base_url.endswith("/api"):
        return f"{normalized_base_url}/tasks"
    return f"{normalized_base_url}/api/tasks"


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
