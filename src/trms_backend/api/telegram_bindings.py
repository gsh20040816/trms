from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from trms_backend.api.request_identity import (
    RequestIdentity,
    build_authenticated_request_identity_dependency,
)
from trms_backend.application.telegram_binding_oauth import (
    TelegramBindingAuthorizationConsumedError,
    TelegramBindingAuthorizationExpiredError,
    TelegramBindingAuthorizationInvalidError,
    TelegramBindingOauthService,
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
    binding_oauth_service: TelegramBindingOauthService,
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

    def ensure_member_binding_role(identity: RequestIdentity) -> str:
        if identity.user is None or UserRole.MEMBER not in identity.user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="actor is not allowed to bind telegram account",
            )
        return identity.user.actor_id

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

    @router.get("/api/telegram-bindings/oauth/{token}")
    def get_telegram_binding_oauth_status(token: str):
        try:
            return {"item": binding_oauth_service.get_authorization_view(token=token)}
        except TelegramBindingAuthorizationInvalidError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error

    @router.post("/api/telegram-bindings/oauth/{token}/confirm")
    def confirm_telegram_binding_oauth(
        token: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        member_id = ensure_member_binding_role(identity)
        try:
            binding = binding_oauth_service.confirm_authorization(
                token=token,
                member_id=member_id,
            )
        except TelegramBindingAuthorizationInvalidError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        except TelegramBindingAuthorizationExpiredError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except TelegramBindingAuthorizationConsumedError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except TelegramAccountBindingConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        return {"item": binding}

    return router
