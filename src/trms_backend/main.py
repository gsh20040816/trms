import os

from fastapi import FastAPI, Request

from trms_backend.application.material_submission import MaterialSubmissionService
from trms_backend.api.cli_compatibility import reject_incompatible_cli_request
from trms_backend.api.confirmations import build_confirmation_router
from trms_backend.api.exports import build_export_router
from trms_backend.api.invoices import build_invoice_router
from trms_backend.api.materials import build_material_router
from trms_backend.api.recognitions import build_recognition_router
from trms_backend.api.splits import build_split_router
from trms_backend.api.tasks import build_task_router
from trms_backend.api.telegram_bindings import build_telegram_binding_router
from trms_backend.domain.global_invoice_config import GlobalInvoiceConfig
from trms_backend.domain.materials import MaterialFileStorage
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import (
    SqlAlchemyAutomaticReminderTaskRepository,
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
from trms_backend.infrastructure.storage import LocalMaterialFileStorage


def create_app(
    database_url: str | None = None,
    global_invoice_config: GlobalInvoiceConfig | None = None,
    material_file_storage: MaterialFileStorage | None = None,
) -> FastAPI:
    app = FastAPI(title="TRMS API")
    session_factory = build_session_factory(
        database_url or os.getenv("DATABASE_URL", "sqlite:///./trms.db")
    )
    init_database(session_factory)
    global_invoice_config_repository = SqlAlchemyGlobalInvoiceConfigRepository(session_factory)
    if global_invoice_config is not None:
        global_invoice_config_repository.set(global_invoice_config)
    task_repository = SqlAlchemyTaskRepository(session_factory)
    material_repository = SqlAlchemyMaterialRepository(session_factory)
    if material_file_storage is None:
        material_file_storage = LocalMaterialFileStorage(
            os.getenv("MATERIAL_STORAGE_DIR", "./data/materials")
        )
    material_reminder_repository = SqlAlchemyMaterialReminderRepository(session_factory)
    automatic_reminder_task_repository = SqlAlchemyAutomaticReminderTaskRepository(session_factory)
    export_job_repository = SqlAlchemyExportJobRepository(session_factory)
    invoice_repository = SqlAlchemyInvoiceRepository(session_factory)
    validation_repository = SqlAlchemyValidationRepository(session_factory)
    recognition_task_repository = SqlAlchemyRecognitionTaskRepository(session_factory)
    telegram_account_binding_repository = SqlAlchemyTelegramAccountBindingRepository(session_factory)
    split_repository = SqlAlchemyExpenseSplitRepository(session_factory)
    confirmation_repository = SqlAlchemyConfirmationRepository(session_factory)
    material_submission_service = MaterialSubmissionService(
        task_repository,
        material_repository,
        material_file_storage,
        recognition_task_repository,
    )

    @app.middleware("http")
    async def enforce_cli_compatibility(request: Request, call_next):
        rejection = reject_incompatible_cli_request(request)
        if rejection is not None:
            return rejection
        return await call_next(request)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(
        build_task_router(
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
        )
    )
    app.include_router(
        build_export_router(
            task_repository,
            export_job_repository,
            invoice_repository,
            material_repository,
            material_file_storage,
            validation_repository,
            split_repository,
            confirmation_repository,
        )
    )
    app.include_router(
        build_material_router(
            task_repository,
            material_repository,
            material_submission_service,
        )
    )
    app.include_router(
        build_recognition_router(
            task_repository,
            material_repository,
            invoice_repository,
            validation_repository,
            recognition_task_repository,
        )
    )
    app.include_router(
        build_invoice_router(
            task_repository,
            material_repository,
            invoice_repository,
            validation_repository,
            recognition_task_repository,
        )
    )
    app.include_router(
        build_split_router(
            task_repository,
            material_repository,
            invoice_repository,
            split_repository,
        )
    )
    app.include_router(
        build_confirmation_router(invoice_repository, split_repository, confirmation_repository)
    )
    app.include_router(build_telegram_binding_router(telegram_account_binding_repository))
    return app


app = create_app()
