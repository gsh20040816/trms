from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

import uvicorn

from trms_backend.application.async_jobs import AsyncJobWorker
from trms_backend.runtime_config import RuntimeConfig, load_runtime_config


def run_api_command(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the TRMS backend API server.")
    parser.add_argument("--host", help="Override TRMS_API_HOST for this process.")
    parser.add_argument("--port", help="Override TRMS_API_PORT for this process.")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto reload for local development.",
    )
    args = parser.parse_args(list(argv))

    config = load_runtime_config(api_host=args.host, api_port=args.port)
    os.environ["TRMS_API_HOST"] = config.api_host
    os.environ["TRMS_API_PORT"] = str(config.api_port)

    uvicorn.run(
        "trms_backend.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=args.reload,
    )
    return 0


def build_async_job_worker(config: RuntimeConfig) -> AsyncJobWorker:
    return AsyncJobWorker(config.async_jobs)


def run_worker_command(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the TRMS async job worker.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one polling iteration and exit.",
    )
    args = parser.parse_args(list(argv))

    config = load_runtime_config()
    worker = build_async_job_worker(config)
    if args.once:
        worker.run_once()
        return 0

    worker.run_forever()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else list(os.sys.argv[1:])
    if arguments and arguments[0] == "worker":
        return run_worker_command(arguments[1:])
    if arguments and arguments[0] == "api":
        return run_api_command(arguments[1:])
    return run_api_command(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
