import os

from fastapi import FastAPI

from trms_backend.api.confirmations import build_confirmation_router
from trms_backend.api.invoices import build_invoice_router
from trms_backend.api.materials import build_material_router
from trms_backend.api.splits import build_split_router
from trms_backend.api.tasks import build_task_router
from trms_backend.domain.global_invoice_config import GlobalInvoiceConfig
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import (
    SqlAlchemyConfirmationRepository,
    SqlAlchemyInvoiceRepository,
    SqlAlchemyExpenseSplitRepository,
    SqlAlchemyGlobalInvoiceConfigRepository,
    SqlAlchemyMaterialRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyValidationRepository,
)


def create_app(
    database_url: str | None = None,
    global_invoice_config: GlobalInvoiceConfig | None = None,
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
    invoice_repository = SqlAlchemyInvoiceRepository(session_factory)
    validation_repository = SqlAlchemyValidationRepository(session_factory)
    split_repository = SqlAlchemyExpenseSplitRepository(session_factory)
    confirmation_repository = SqlAlchemyConfirmationRepository(session_factory)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(
        build_task_router(
            task_repository,
            global_invoice_config_repository,
            invoice_repository,
            validation_repository,
            split_repository,
            confirmation_repository,
        )
    )
    app.include_router(build_material_router(task_repository, material_repository))
    app.include_router(
        build_invoice_router(
            task_repository,
            material_repository,
            invoice_repository,
            validation_repository,
        )
    )
    app.include_router(build_split_router(task_repository, invoice_repository, split_repository))
    app.include_router(
        build_confirmation_router(invoice_repository, split_repository, confirmation_repository)
    )
    return app


app = create_app()
