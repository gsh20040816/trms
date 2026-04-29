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
from trms_backend.domain.system_ai_provider_config import (
    SystemAiProviderConfigPatch,
    SystemAiProviderConfigRepository,
    SystemAiProviderConfigSummary,
    summarize_system_ai_provider_override,
)
from trms_backend.runtime_config import RuntimeConfig, apply_system_ai_provider_overrides


class RuntimeSummaryResponse(BaseModel):
    environment: str
    public_api_base_url: str
    async_job_mode: str
    file_storage_backend: str
    llm_provider_configured: bool
    text_llm_provider_configured: bool
    vlm_provider_configured: bool
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
    system_ai_provider_config: dict[str, SystemAiProviderConfigSummary]
    runtime: RuntimeSummaryResponse
    user_counts: SystemUserCountSummary


def build_system_router(
    auth_repository: AuthRepository,
    global_invoice_config_repository: GlobalInvoiceConfigRepository,
    system_ai_provider_config_repository: SystemAiProviderConfigRepository,
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
        stored_system_ai_provider_config = system_ai_provider_config_repository.get()
        effective_runtime_config = apply_system_ai_provider_overrides(
            runtime_config,
            stored_system_ai_provider_config,
        )
        return SystemDashboardResponse(
            global_invoice_config=global_invoice_config_repository.get(),
            system_ai_provider_config={
                "text_llm": summarize_system_ai_provider_override(
                    (
                        stored_system_ai_provider_config.text_llm
                        if stored_system_ai_provider_config is not None
                        else SystemAiProviderConfigPatch().text_llm
                    )
                ),
                "vlm": summarize_system_ai_provider_override(
                    (
                        stored_system_ai_provider_config.vlm
                        if stored_system_ai_provider_config is not None
                        else SystemAiProviderConfigPatch().vlm
                    )
                ),
            },
            runtime=RuntimeSummaryResponse(
                environment=effective_runtime_config.environment,
                public_api_base_url=effective_runtime_config.public_api_base_url,
                async_job_mode=effective_runtime_config.async_jobs.mode,
                file_storage_backend=effective_runtime_config.file_storage.backend,
                llm_provider_configured=effective_runtime_config.llm_provider is not None,
                text_llm_provider_configured=effective_runtime_config.text_llm_provider is not None,
                vlm_provider_configured=effective_runtime_config.vlm_provider is not None,
                allow_admin_self_register=effective_runtime_config.auth.allow_admin_self_register,
                bootstrap_admin_configured=effective_runtime_config.auth.bootstrap_admin_token is not None,
                telegram_inbound_configured=effective_runtime_config.auth.telegram_inbound_token is not None,
                email_inbound_configured=effective_runtime_config.auth.email_inbound_token is not None,
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

    @router.put("/recognition-provider-config")
    def update_recognition_provider_config(
        payload: SystemAiProviderConfigPatch,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ) -> dict[str, SystemAiProviderConfigSummary]:
        ensure_system_admin(identity)
        saved = system_ai_provider_config_repository.patch(payload)
        return {
            "text_llm": summarize_system_ai_provider_override(saved.text_llm),
            "vlm": summarize_system_ai_provider_override(saved.vlm),
        }

    return router
