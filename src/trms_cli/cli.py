from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = os.getenv("TRMS_API_BASE_URL", "http://127.0.0.1:8000")


class CliError(Exception):
    """Raised when a CLI command cannot complete successfully."""


def fetch_json(url: str) -> tuple[int, object]:
    request = Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
            return response.status, payload
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        if detail:
            raise CliError(f"request failed with status {error.code}: {detail}") from error
        raise CliError(f"request failed with status {error.code}") from error
    except URLError as error:
        raise CliError(f"unable to reach TRMS API: {error.reason}") from error
    except json.JSONDecodeError as error:
        raise CliError("TRMS API returned invalid JSON") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trms-cli", description="TRMS command line client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health_parser = subparsers.add_parser("health", help="check TRMS API health")
    health_parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="TRMS API base URL, defaults to TRMS_API_BASE_URL or http://127.0.0.1:8000",
    )
    health_parser.set_defaults(handler=run_health_command)

    return parser


def run_health_command(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    status_code, payload = fetch_json(f"{base_url}/health")
    if status_code != 200:
        raise CliError(f"health endpoint returned unexpected status {status_code}")
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise CliError("TRMS API health payload is not ready")

    print("TRMS API health: ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.handler(args)
    except CliError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
