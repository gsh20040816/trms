from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from trms_backend.api.request_identity import (
    RequestIdentity,
    build_authenticated_request_identity_dependency,
)
from trms_backend.api.error_responses import ensure_request_id
from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
from trms_backend.domain.auth import AuthRepository, AuthenticatedUser, UserRole
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
    system_timezone: str
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


class SystemUserRoleSummary(BaseModel):
    id: str
    actor_id: str
    username: str
    display_name: str
    student_id: str | None = None
    roles: list[UserRole] = Field(default_factory=list)


class SystemAdminRoleGrantResponse(BaseModel):
    user: AuthenticatedUser
    role: UserRole
    already_assigned: bool


def build_system_user_role_summary(user: AuthenticatedUser) -> SystemUserRoleSummary:
    return SystemUserRoleSummary(
        id=user.id,
        actor_id=user.actor_id,
        username=user.username,
        display_name=user.display_name,
        student_id=user.member_code,
        roles=user.roles,
    )


def build_system_router(
    auth_repository: AuthRepository,
    audit_log_repository: AuditLogRepository,
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
                system_timezone=effective_runtime_config.system_timezone,
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

    @router.get("/users/search")
    def search_system_users(
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        keyword: Annotated[str, Query(min_length=1, max_length=128)],
        limit: Annotated[int, Query(ge=1, le=20)] = 10,
    ):
        ensure_system_admin(identity)
        users = auth_repository.search_users(
            keyword=keyword,
            roles=(UserRole.MEMBER, UserRole.ADMIN, UserRole.SYSTEM_ADMIN),
            limit=limit,
        )
        return {
            "items": [build_system_user_role_summary(user) for user in users]
        }

    @router.put("/users/{user_id}/roles/admin")
    def grant_admin_role(
        user_id: str,
        request: Request,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ) -> SystemAdminRoleGrantResponse:
        ensure_system_admin(identity)
        assert identity.user is not None

        grant_result = auth_repository.grant_role_to_user(
            user_id=user_id,
            role=UserRole.ADMIN,
        )
        if grant_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user not found",
            )

        user, already_assigned = grant_result
        audit_log_repository.create(
            AuditLogCreate(
                actor_id=identity.user.actor_id,
                object_type="user_account",
                object_id=user.id,
                action="grant_user_role",
                result=AuditLogResult.SUCCEEDED,
                summary=f"granted admin role to user {user.username}",
                detail={
                    "user_id": user.id,
                    "username": user.username,
                    "granted_role": UserRole.ADMIN.value,
                    "already_assigned": already_assigned,
                },
                request_id=ensure_request_id(request),
            )
        )
        return SystemAdminRoleGrantResponse(
            user=user,
            role=UserRole.ADMIN,
            already_assigned=already_assigned,
        )

    return router
