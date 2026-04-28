from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from trms_backend.application.email_material_submission import EmailMaterialSubmissionService
from trms_backend.application.material_deletion import MaterialDeletionService
from trms_backend.application.metrics import InMemoryMetricsCollector, MetricsCollector
from trms_backend.application.material_submission import MaterialSubmissionService
from trms_backend.application.recognition_llm import OpenAiCompatibleRecognitionClient
from trms_backend.application.recognition_preparation import RecognitionPreparationService
from trms_backend.application.recognition_runtime import resolve_recognition_llm_capability
from trms_backend.application.telegram_material_submission import (
    TelegramMaterialSubmissionService,
)
from trms_backend.api.cli_compatibility import reject_incompatible_cli_request
from trms_backend.api.error_responses import ensure_request_id, register_error_response_handlers
from trms_backend.api.auth import build_auth_router
from trms_backend.api.confirmations import build_confirmation_router
from trms_backend.api.email_materials import build_email_material_router
from trms_backend.api.exports import build_export_router
from trms_backend.api.invoices import build_invoice_router
from trms_backend.api.materials import build_material_router
from trms_backend.api.recognitions import build_recognition_router
from trms_backend.api.splits import build_split_router
from trms_backend.api.telegram_materials import build_telegram_material_router
from trms_backend.api.tasks import build_task_router
from trms_backend.api.telegram_bindings import build_telegram_binding_router
from trms_backend.domain.global_invoice_config import GlobalInvoiceConfig
from trms_backend.domain.materials import MaterialFileStorage
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import (
    SqlAlchemyAutomaticReminderTaskRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyAuthRepository,
    SqlAlchemyConfirmationRepository,
    SqlAlchemyExportJobRepository,
    SqlAlchemyInvoiceRepository,
    SqlAlchemyExpenseSplitRepository,
    SqlAlchemyGlobalInvoiceConfigRepository,
    SqlAlchemyMaterialReminderRepository,
    SqlAlchemyMaterialRepository,
    SqlAlchemyRecognitionTaskRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyTelegramAccountBindingRepository,
    SqlAlchemyValidationRepository,
)
from trms_backend.infrastructure.storage import build_material_file_storage
from trms_backend.request_context_logging import (
    bind_request_id,
    install_request_id_log_record_factory,
    reset_request_id,
)
from trms_backend.runtime_config import RuntimeConfig, load_runtime_config


def create_app(
    database_url: str | None = None,
    global_invoice_config: GlobalInvoiceConfig | None = None,
    material_file_storage: MaterialFileStorage | None = None,
    runtime_config: RuntimeConfig | None = None,
    recognition_llm_client: OpenAiCompatibleRecognitionClient | None = None,
    metrics_collector: MetricsCollector | None = None,
) -> FastAPI:
    config = runtime_config or load_runtime_config(database_url=database_url)
    install_request_id_log_record_factory()
    app = FastAPI(title="TRMS API")
    register_error_response_handlers(app)
    app.state.runtime_config = config
    app.state.async_job_config = config.async_jobs
    app.state.recognition_llm_capability = resolve_recognition_llm_capability(config)
    app.state.metrics_collector = metrics_collector or InMemoryMetricsCollector()
    if recognition_llm_client is None and config.llm_provider is not None:
        recognition_llm_client = OpenAiCompatibleRecognitionClient(config.llm_provider)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    session_factory = build_session_factory(config.database_url)
    init_database(
        session_factory,
        allow_schema_bootstrap=config.environment != "production",
    )
    global_invoice_config_repository = SqlAlchemyGlobalInvoiceConfigRepository(session_factory)
    auth_repository = SqlAlchemyAuthRepository(session_factory)
    if global_invoice_config is not None:
        global_invoice_config_repository.set(global_invoice_config)
    task_repository = SqlAlchemyTaskRepository(session_factory)
    material_repository = SqlAlchemyMaterialRepository(session_factory)
    if material_file_storage is None:
        material_file_storage = build_material_file_storage(config)
    material_reminder_repository = SqlAlchemyMaterialReminderRepository(session_factory)
    automatic_reminder_task_repository = SqlAlchemyAutomaticReminderTaskRepository(session_factory)
    export_job_repository = SqlAlchemyExportJobRepository(session_factory)
    invoice_repository = SqlAlchemyInvoiceRepository(session_factory)
    validation_repository = SqlAlchemyValidationRepository(session_factory)
    recognition_task_repository = SqlAlchemyRecognitionTaskRepository(session_factory)
    telegram_account_binding_repository = SqlAlchemyTelegramAccountBindingRepository(session_factory)
    split_repository = SqlAlchemyExpenseSplitRepository(session_factory)
    confirmation_repository = SqlAlchemyConfirmationRepository(session_factory)
    audit_log_repository = SqlAlchemyAuditLogRepository(session_factory)
    material_submission_service = MaterialSubmissionService(
        task_repository,
        material_repository,
        material_file_storage,
        recognition_task_repository,
        audit_log_repository,
        app.state.metrics_collector,
    )
    material_deletion_service = MaterialDeletionService(
        task_repository,
        material_repository,
        invoice_repository,
    )
    recognition_preparation_service = RecognitionPreparationService(
        material_repository,
        material_file_storage,
        recognition_task_repository,
        audit_log_repository,
        app.state.recognition_llm_capability,
        recognition_llm_client,
        app.state.metrics_collector,
    )
    email_material_submission_service = EmailMaterialSubmissionService(
        material_submission_service,
    )
    telegram_material_submission_service = TelegramMaterialSubmissionService(
        telegram_account_binding_repository,
        material_submission_service,
    )

    @app.middleware("http")
    async def enforce_cli_compatibility(request: Request, call_next):
        request_id = ensure_request_id(request)
        context_token = bind_request_id(request_id)
        try:
            rejection = reject_incompatible_cli_request(request, request_id=request_id)
            if rejection is not None:
                return rejection
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            reset_request_id(context_token)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(
        build_auth_router(
            auth_repository,
            allow_privileged_self_registration=config.auth.allow_admin_self_register,
            bootstrap_admin_token=(
                config.auth.bootstrap_admin_token.get_secret_value()
                if config.auth.bootstrap_admin_token is not None
                else None
            ),
        )
    )
    app.include_router(
        build_task_router(
            auth_repository,
            task_repository,
            global_invoice_config_repository,
            material_reminder_repository,
            automatic_reminder_task_repository,
            material_repository,
            invoice_repository,
            validation_repository,
            recognition_task_repository,
            split_repository,
            confirmation_repository,
            audit_log_repository,
        )
    )
    app.include_router(
        build_export_router(
            auth_repository,
            task_repository,
            export_job_repository,
            invoice_repository,
            material_repository,
            material_file_storage,
            validation_repository,
            split_repository,
            confirmation_repository,
            audit_log_repository,
            app.state.metrics_collector,
        )
    )
    app.include_router(
        build_material_router(
            auth_repository,
            task_repository,
            material_repository,
            material_submission_service,
            material_deletion_service,
            audit_log_repository,
        )
    )
    app.include_router(
        build_email_material_router(
            email_material_submission_service,
            trusted_inbound_token=(
                config.auth.email_inbound_token.get_secret_value()
                if config.auth.email_inbound_token is not None
                else None
            ),
        )
    )
    app.include_router(
        build_telegram_material_router(
            telegram_material_submission_service,
            trusted_inbound_token=(
                config.auth.telegram_inbound_token.get_secret_value()
                if config.auth.telegram_inbound_token is not None
                else None
            ),
        )
    )
    app.include_router(
        build_recognition_router(
            auth_repository,
            task_repository,
            material_repository,
            invoice_repository,
            validation_repository,
            recognition_task_repository,
            recognition_preparation_service,
            audit_log_repository,
            app.state.metrics_collector,
        )
    )
    app.include_router(
        build_invoice_router(
            auth_repository,
            task_repository,
            material_repository,
            invoice_repository,
            validation_repository,
            recognition_task_repository,
            audit_log_repository,
            app.state.metrics_collector,
        )
    )
    app.include_router(
        build_split_router(
            auth_repository,
            task_repository,
            material_repository,
            invoice_repository,
            split_repository,
            audit_log_repository,
        )
    )
    app.include_router(
        build_confirmation_router(
            auth_repository,
            task_repository,
            material_repository,
            invoice_repository,
            split_repository,
            confirmation_repository,
            audit_log_repository,
        )
    )
    app.include_router(
        build_telegram_binding_router(
            auth_repository,
            telegram_account_binding_repository,
        )
    )
    return app


app = create_app()
