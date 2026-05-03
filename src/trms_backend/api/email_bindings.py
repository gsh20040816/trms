from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from trms_backend.api.request_identity import (
    RequestIdentity,
    build_authenticated_request_identity_dependency,
)
from trms_backend.application.email_binding import (
    EmailBindingService,
    EmailBindingVerificationCodeExpiredError,
    EmailBindingVerificationCodeInvalidError,
    OutboundEmailNotConfiguredError,
)
from trms_backend.domain.auth import AuthRepository, UserRole
from trms_backend.domain.email_bindings import EmailAccountBindingConflictError


class EmailBindingVerificationCodeRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class EmailBindingVerifyRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    code: str = Field(min_length=1, max_length=32)


def build_email_binding_router(
    auth_repository: AuthRepository,
    email_binding_service: EmailBindingService,
) -> APIRouter:
    router = APIRouter(tags=["email-bindings"])
    authenticated_request_identity = build_authenticated_request_identity_dependency(
        auth_repository
    )

    def ensure_member_email_binding_role(identity: RequestIdentity) -> str:
        if identity.user is None or UserRole.MEMBER not in identity.user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="actor is not allowed to manage email bindings",
            )
        return identity.user.actor_id

    @router.get("/api/email-bindings")
    def list_email_bindings(
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        member_id = ensure_member_email_binding_role(identity)
        return {
            "items": email_binding_service.list_bindings(member_id=member_id),
        }

    @router.post("/api/email-bindings/verification-code", status_code=status.HTTP_202_ACCEPTED)
    def send_email_binding_verification_code(
        payload: EmailBindingVerificationCodeRequest,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        member_id = ensure_member_email_binding_role(identity)
        try:
            dispatch_result = email_binding_service.send_verification_code(
                member_id=member_id,
                email=payload.email,
            )
        except OutboundEmailNotConfiguredError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        except EmailAccountBindingConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        return {
            "item": dispatch_result,
        }

    @router.post("/api/email-bindings/verify")
    def verify_email_binding_code(
        payload: EmailBindingVerifyRequest,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        member_id = ensure_member_email_binding_role(identity)
        try:
            binding = email_binding_service.verify_code(
                member_id=member_id,
                email=payload.email,
                code=payload.code,
            )
        except EmailBindingVerificationCodeInvalidError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        except EmailBindingVerificationCodeExpiredError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except EmailAccountBindingConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        return {"item": binding}

    return router
