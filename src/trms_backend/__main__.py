from __future__ import annotations

import argparse
import os

import uvicorn

from trms_backend.runtime_config import load_runtime_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the TRMS backend API server.")
    parser.add_argument("--host", help="Override TRMS_API_HOST for this process.")
    parser.add_argument("--port", help="Override TRMS_API_PORT for this process.")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto reload for local development.",
    )
    args = parser.parse_args()

    config = load_runtime_config(api_host=args.host, api_port=args.port)
    os.environ["TRMS_API_HOST"] = config.api_host
    os.environ["TRMS_API_PORT"] = str(config.api_port)

    uvicorn.run(
        "trms_backend.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
