from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from trms_cli.token_store import TokenStoreError, save_token_session

DEFAULT_BASE_URL = os.getenv("TRMS_API_BASE_URL", "http://127.0.0.1:8000")
CLI_JSON_SCHEMA_VERSION = "trms-cli.v1"
ACCESS_TOKEN_ENV = "TRMS_CLI_ACCESS_TOKEN"
REFRESH_TOKEN_ENV = "TRMS_CLI_REFRESH_TOKEN"


class CliError(Exception):
    """Raised when a CLI command cannot complete successfully."""

    def __init__(self, message: str, *, code: str = "cli_error") -> None:
        super().__init__(message)
        self.code = code


def emit_json(payload: dict[str, object], *, stream: object | None = None) -> None:
    print(json.dumps(payload, ensure_ascii=False), file=stream or sys.stdout)


def fetch_json(url: str) -> tuple[int, object]:
    request = Request(url, method="GET", headers={"Accept": "application/json"})
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
