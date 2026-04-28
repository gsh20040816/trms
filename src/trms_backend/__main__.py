from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

import uvicorn

from trms_backend.application.async_jobs import AsyncJobWorker
from trms_backend.application.export_async_jobs import ExportAsyncJobProcessor
from trms_backend.application.recognition_async_jobs import RecognitionAsyncJobProcessor
from trms_backend.application.recognition_llm import OpenAiCompatibleRecognitionClient
from trms_backend.application.recognition_preparation import RecognitionPreparationService
from trms_backend.application.recognition_runtime import resolve_recognition_llm_capability
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import (
    SqlAlchemyConfirmationRepository,
    SqlAlchemyExportJobRepository,
    SqlAlchemyExpenseSplitRepository,
    SqlAlchemyInvoiceRepository,
    SqlAlchemyMaterialRepository,
    SqlAlchemyRecognitionTaskRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyValidationRepository,
)
from trms_backend.infrastructure.storage import build_material_file_storage
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
    session_factory = build_session_factory(config.database_url)
    init_database(
        session_factory,
        allow_schema_bootstrap=config.environment != "production",
    )
    material_repository = SqlAlchemyMaterialRepository(session_factory)
    task_repository = SqlAlchemyTaskRepository(session_factory)
    invoice_repository = SqlAlchemyInvoiceRepository(session_factory)
    validation_repository = SqlAlchemyValidationRepository(session_factory)
    recognition_task_repository = SqlAlchemyRecognitionTaskRepository(session_factory)
    export_job_repository = SqlAlchemyExportJobRepository(session_factory)
    split_repository = SqlAlchemyExpenseSplitRepository(session_factory)
    confirmation_repository = SqlAlchemyConfirmationRepository(session_factory)
    material_file_storage = build_material_file_storage(config)
    recognition_llm_client = (
        OpenAiCompatibleRecognitionClient(config.llm_provider)
        if config.llm_provider is not None
        else None
    )
    recognition_preparation_service = RecognitionPreparationService(
        material_repository,
        material_file_storage,
        recognition_task_repository,
        resolve_recognition_llm_capability(config),
        recognition_llm_client,
    )
    return AsyncJobWorker(
        config.async_jobs,
        processors=(
            RecognitionAsyncJobProcessor(
                task_repository=task_repository,
                material_repository=material_repository,
                invoice_repository=invoice_repository,
                validation_repository=validation_repository,
                recognition_task_repository=recognition_task_repository,
                recognition_preparation_service=recognition_preparation_service,
            ),
            ExportAsyncJobProcessor(
                task_repository=task_repository,
                export_job_repository=export_job_repository,
                invoice_repository=invoice_repository,
                material_repository=material_repository,
                material_file_storage=material_file_storage,
                validation_repository=validation_repository,
                split_repository=split_repository,
                confirmation_repository=confirmation_repository,
            ),
        ),
    )


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
