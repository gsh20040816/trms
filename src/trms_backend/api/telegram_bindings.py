from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from trms_backend.api.request_identity import (
    RequestIdentity,
    build_authenticated_request_identity_dependency,
)
from trms_backend.domain.auth import AuthRepository, UserRole
from trms_backend.domain.telegram_bindings import (
    TelegramAccountBindingConflictError,
    TelegramAccountBindingRepository,
    TelegramAccountBindingUpsert,
    TelegramSubmissionIdentityResolver,
)


class TelegramAccountBindingRequest(BaseModel):
    member_id: str = Field(min_length=1)
    telegram_username: str | None = Field(default=None, max_length=64)


def build_telegram_binding_router(
    auth_repository: AuthRepository,
    binding_repository: TelegramAccountBindingRepository,
) -> APIRouter:
    router = APIRouter(tags=["telegram-bindings"])
    submission_identity_resolver = TelegramSubmissionIdentityResolver(binding_repository)
    authenticated_request_identity = build_authenticated_request_identity_dependency(
        auth_repository
    )

    def ensure_telegram_binding_management_role(identity: RequestIdentity) -> None:
        if identity.role not in {UserRole.ADMIN, UserRole.SYSTEM_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="actor is not allowed to manage telegram account bindings",
            )

    @router.put("/api/telegram-bindings/{telegram_user_id}")
    def upsert_telegram_account_binding(
        telegram_user_id: int,
        payload: TelegramAccountBindingRequest,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        ensure_telegram_binding_management_role(identity)
        try:
            binding = binding_repository.upsert(
                TelegramAccountBindingUpsert(
                    telegram_user_id=telegram_user_id,
                    member_id=payload.member_id,
                    telegram_username=payload.telegram_username,
                )
            )
        except TelegramAccountBindingConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        return {"item": binding}

    @router.get("/api/telegram-bindings/{telegram_user_id}")
    def get_telegram_account_binding(
        telegram_user_id: int,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        ensure_telegram_binding_management_role(identity)
        binding = binding_repository.get_by_telegram_user_id(telegram_user_id)
        if binding is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="telegram account binding not found",
            )
        return {"item": binding}

    @router.get("/api/telegram-bindings/{telegram_user_id}/submission-identity")
    def resolve_telegram_submission_identity(
        telegram_user_id: int,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        ensure_telegram_binding_management_role(identity)
        return {"item": submission_identity_resolver.resolve(telegram_user_id)}

    return router
