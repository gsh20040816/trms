from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from trms_backend.api.request_identity import (
    RequestIdentity,
    build_authenticated_request_identity_dependency,
)
from trms_backend.domain.auth import AuthRepository, UserRole
from trms_backend.domain.global_invoice_config import (
    GlobalInvoiceConfig,
    GlobalInvoiceConfigRepository,
)
from trms_backend.runtime_config import RuntimeConfig


class RuntimeSummaryResponse(BaseModel):
    environment: str
    public_api_base_url: str
    async_job_mode: str
    file_storage_backend: str
    llm_provider_configured: bool
    allow_admin_self_register: bool
    bootstrap_admin_configured: bool
    telegram_inbound_configured: bool
    email_inbound_configured: bool


class SystemUserCountSummary(BaseModel):
    member: int
    admin: int
    system_admin: int


class SystemDashboardResponse(BaseModel):
    service_health: str = Field(default="ok")
    global_invoice_config: GlobalInvoiceConfig | None = None
    runtime: RuntimeSummaryResponse
    user_counts: SystemUserCountSummary


def build_system_router(
    auth_repository: AuthRepository,
    global_invoice_config_repository: GlobalInvoiceConfigRepository,
    runtime_config: RuntimeConfig,
) -> APIRouter:
    router = APIRouter(prefix="/api/system", tags=["system"])
    authenticated_request_identity = build_authenticated_request_identity_dependency(
        auth_repository
    )

    def ensure_system_admin(identity: RequestIdentity) -> None:
        if identity.role is not UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="actor is not allowed to manage system settings",
            )

    def build_dashboard_response() -> SystemDashboardResponse:
        return SystemDashboardResponse(
            global_invoice_config=global_invoice_config_repository.get(),
            runtime=RuntimeSummaryResponse(
                environment=runtime_config.environment,
                public_api_base_url=runtime_config.public_api_base_url,
                async_job_mode=runtime_config.async_jobs.mode,
                file_storage_backend=runtime_config.file_storage.backend,
                llm_provider_configured=runtime_config.llm_provider is not None,
                allow_admin_self_register=runtime_config.auth.allow_admin_self_register,
                bootstrap_admin_configured=runtime_config.auth.bootstrap_admin_token is not None,
                telegram_inbound_configured=runtime_config.auth.telegram_inbound_token is not None,
                email_inbound_configured=runtime_config.auth.email_inbound_token is not None,
            ),
            user_counts=SystemUserCountSummary(
                member=auth_repository.count_users_with_roles((UserRole.MEMBER,)),
                admin=auth_repository.count_users_with_roles((UserRole.ADMIN,)),
                system_admin=auth_repository.count_users_with_roles(
                    (UserRole.SYSTEM_ADMIN,)
                ),
            ),
        )

    @router.get("/dashboard")
    def get_system_dashboard(
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ) -> SystemDashboardResponse:
        ensure_system_admin(identity)
        return build_dashboard_response()

    @router.put("/global-invoice-config")
    def update_global_invoice_config(
        payload: GlobalInvoiceConfig,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ) -> GlobalInvoiceConfig:
        ensure_system_admin(identity)
        return global_invoice_config_repository.set(payload)

    return router
