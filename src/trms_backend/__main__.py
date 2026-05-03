from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence

import uvicorn

from trms_backend.application.async_jobs import AsyncJobWorker
from trms_backend.application.email_inbox_polling import (
    EmailInboxImportProcessor,
    EmailInboxPollingProcessor,
    ImapEmailInboxClient,
    StaticEmailInboxClient,
)
from trms_backend.application.export_async_jobs import ExportAsyncJobProcessor
from trms_backend.application.metrics import InMemoryMetricsCollector
from trms_backend.application.email_material_submission import EmailMaterialSubmissionService
from trms_backend.application.material_submission import MaterialSubmissionService
from trms_backend.application.outbound_email import SmtpOutboundEmailSender
from trms_backend.application.recognition_async_jobs import RecognitionAsyncJobProcessor
from trms_backend.application.recognition_llm import (
    RoutedRecognitionClient,
)
from trms_backend.application.recognition_preparation import RecognitionPreparationService
from trms_backend.application.recognition_runtime import resolve_recognition_llm_capability
from trms_backend.domain.email_bindings import EmailSubmissionIdentityResolver
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyConfirmationRepository,
    SqlAlchemyEmailAccountBindingRepository,
    SqlAlchemyEmailInboxRecordRepository,
    SqlAlchemyExportJobRepository,
    SqlAlchemyExpenseSplitRepository,
    SqlAlchemyInvoiceRepository,
    SqlAlchemyMaterialRepository,
    SqlAlchemyRecognitionTaskRepository,
    SqlAlchemySystemAiProviderConfigRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyValidationRepository,
)
from trms_backend.infrastructure.storage import build_material_file_storage
from trms_backend.logging_safety import sanitize_log_fields
from trms_backend.runtime_config import (
    RuntimeConfig,
    apply_system_ai_provider_overrides,
    load_runtime_config,
    load_runtime_environment_variables,
)

LOGGER = logging.getLogger("trms_backend.worker")


def configure_worker_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=False,
    )


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

    environment_variables = load_runtime_environment_variables()
    config = load_runtime_config(
        env=environment_variables,
        api_host=args.host,
        api_port=args.port,
    )
    os.environ.update(environment_variables)
    os.environ["TRMS_API_HOST"] = config.api_host
    os.environ["TRMS_API_PORT"] = str(config.api_port)

    uvicorn.run(
        "trms_backend.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=args.reload,
    )
    return 0


def build_async_job_worker(config: RuntimeConfig) -> tuple[AsyncJobWorker, RuntimeConfig]:
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
    email_account_binding_repository = SqlAlchemyEmailAccountBindingRepository(session_factory)
    email_inbox_record_repository = SqlAlchemyEmailInboxRecordRepository(session_factory)
    split_repository = SqlAlchemyExpenseSplitRepository(session_factory)
    confirmation_repository = SqlAlchemyConfirmationRepository(session_factory)
    audit_log_repository = SqlAlchemyAuditLogRepository(session_factory)
    system_ai_provider_config_repository = SqlAlchemySystemAiProviderConfigRepository(session_factory)
    def resolve_effective_runtime_config() -> RuntimeConfig:
        return apply_system_ai_provider_overrides(
            config,
            system_ai_provider_config_repository.get(),
        )

    effective_config = resolve_effective_runtime_config()
    material_file_storage = build_material_file_storage(effective_config)
    email_inbox_client = (
        ImapEmailInboxClient(effective_config.email_inbox)
        if effective_config.email_inbox is not None
        else StaticEmailInboxClient([])
    )
    metrics_collector = InMemoryMetricsCollector()
    recognition_llm_client = (
        RoutedRecognitionClient(
            text_provider_config_resolver=lambda: resolve_effective_runtime_config().text_llm_provider,
            vlm_provider_config_resolver=lambda: resolve_effective_runtime_config().vlm_provider,
        )
    )
    recognition_preparation_service = RecognitionPreparationService(
        material_repository,
        material_file_storage,
        recognition_task_repository,
        audit_log_repository,
        resolve_recognition_llm_capability(effective_config),
        recognition_llm_client,
        metrics_collector,
    )
    material_submission_service = MaterialSubmissionService(
        task_repository,
        material_repository,
        material_file_storage,
        recognition_task_repository,
        audit_log_repository,
        metrics_collector,
    )
    outbound_email_sender = (
        SmtpOutboundEmailSender(effective_config.outbound_email)
        if effective_config.outbound_email is not None
        else None
    )
    email_material_submission_service = EmailMaterialSubmissionService(
        material_submission_service=material_submission_service,
        task_repository=task_repository,
        submission_identity_resolver=EmailSubmissionIdentityResolver(
            email_account_binding_repository
        ),
    )
    recognition_worker_max_workers = _resolve_recognition_worker_max_workers(
        config.database_url,
        effective_config.async_jobs.worker_concurrency,
    )
    if recognition_worker_max_workers != effective_config.async_jobs.worker_concurrency:
        LOGGER.warning(
            "recognition_worker_sqlite_serialized %s",
            sanitize_log_fields(
                {
                    "database_url": config.database_url,
                    "configured_max_workers": effective_config.async_jobs.worker_concurrency,
                    "effective_max_workers": recognition_worker_max_workers,
                }
            ),
        )
    return (
        AsyncJobWorker(
            effective_config.async_jobs,
            processors=(
                EmailInboxPollingProcessor(
                    email_inbox_client=email_inbox_client,
                    email_inbox_record_repository=email_inbox_record_repository,
                    email_submission_identity_resolver=EmailSubmissionIdentityResolver(
                        email_account_binding_repository
                    ),
                    task_repository=task_repository,
                    raw_email_storage=material_file_storage,
                    audit_log_repository=audit_log_repository,
                ),
                EmailInboxImportProcessor(
                    email_inbox_record_repository=email_inbox_record_repository,
                    raw_email_storage=material_file_storage,
                    email_material_submission_service=email_material_submission_service,
                    outbound_email_sender=outbound_email_sender,
                    audit_log_repository=audit_log_repository,
                ),
                RecognitionAsyncJobProcessor(
                    task_repository=task_repository,
                    material_repository=material_repository,
                    invoice_repository=invoice_repository,
                    validation_repository=validation_repository,
                    recognition_task_repository=recognition_task_repository,
                    split_repository=split_repository,
                    confirmation_repository=confirmation_repository,
                    recognition_preparation_service=recognition_preparation_service,
                    max_workers=recognition_worker_max_workers,
                    metrics_collector=metrics_collector,
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
                    audit_log_repository=audit_log_repository,
                    metrics_collector=metrics_collector,
                ),
            ),
        ),
        effective_config,
    )


def _resolve_recognition_worker_max_workers(
    database_url: str,
    configured_max_workers: int,
) -> int:
    if configured_max_workers <= 1:
        return 1
    if database_url.strip().lower().startswith("sqlite"):
        return 1
    return configured_max_workers


def run_worker_command(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the TRMS async job worker.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one polling iteration and exit.",
    )
    args = parser.parse_args(list(argv))

    configure_worker_logging()
    config = load_runtime_config(env=load_runtime_environment_variables())
    worker_bundle = build_async_job_worker(config)
    if isinstance(worker_bundle, tuple):
        worker, effective_config = worker_bundle
    else:
        worker = worker_bundle
        effective_config = config
    LOGGER.info(
        "worker_startup %s",
        {
            "mode": worker.mode,
            "poll_interval_seconds": worker.poll_interval_seconds,
            "worker_concurrency": worker.worker_concurrency,
            "registered_job_types": list(worker.registered_job_types),
            "environment": config.environment,
            "file_storage": effective_config.file_storage.to_safe_log_fields(),
            "text_llm_provider": (
                effective_config.text_llm_provider.to_safe_log_fields()
                if effective_config.text_llm_provider is not None
                else None
            ),
            "vlm_provider": (
                effective_config.vlm_provider.to_safe_log_fields()
                if effective_config.vlm_provider is not None
                else None
            ),
        },
    )
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
