from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ValidationError

from trms_backend.api.error_responses import ensure_request_id
from trms_backend.api.request_identity import (
    RequestIdentity,
    build_optional_request_identity_dependency,
)
from trms_backend.api.request_identity_http import resolve_required_actor_request_field
from trms_backend.api.request_task_access import TaskAccessScope, resolve_task_access_scope
from trms_backend.application.expense_audit import (
    record_split_confirmation_audit,
    record_split_confirmation_rejection_audit,
)
from trms_backend.domain.audit_logs import AuditLogRepository
from trms_backend.domain.auth import AuthRepository

from trms_backend.domain.confirmations import (
    ConfirmationRepository,
    ConfirmationStatus,
    MemberConfirmationSubmit,
)
from trms_backend.domain.invoices import InvoiceRepository
from trms_backend.domain.splits import ExpenseSplitRepository
from trms_backend.domain.tasks import TaskRepository


class MemberConfirmationSubmitRequest(BaseModel):
    actor_id: str | None = None
    member_id: str | None = None
    status: ConfirmationStatus
    dispute_reason: str | None = None

    def to_domain(self, *, actor_id: str, member_id: str) -> MemberConfirmationSubmit:
        return MemberConfirmationSubmit.model_validate(
            {
                "actor_id": actor_id,
                "member_id": member_id,
                "status": self.status,
                "dispute_reason": self.dispute_reason,
            }
        )


def build_confirmation_router(
    auth_repository: AuthRepository,
    task_repository: TaskRepository,
    invoice_repository: InvoiceRepository,
    split_repository: ExpenseSplitRepository,
    confirmation_repository: ConfirmationRepository,
    audit_log_repository: AuditLogRepository,
) -> APIRouter:
    router = APIRouter(tags=["confirmations"])
    optional_request_identity = build_optional_request_identity_dependency(auth_repository)

    @router.put("/api/splits/{split_id}/confirmation")
    def submit_confirmation(
        split_id: str,
        request: Request,
        payload: MemberConfirmationSubmitRequest,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
        split = split_repository.get(split_id)
        if split is None or not split.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="split not found")
        invoice = invoice_repository.get(split.invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")
        task = task_repository.get(invoice.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        request_id = ensure_request_id(request)

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            payload.actor_id,
            field_name="actor_id",
        )
        resolved_member_id = resolve_required_actor_request_field(
            identity,
            payload.member_id,
            field_name="member_id",
        )
        try:
            submit_payload = payload.to_domain(
                actor_id=resolved_actor_id,
                member_id=resolved_member_id,
            )
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error

        if submit_payload.actor_id != submit_payload.member_id:
            record_split_confirmation_rejection_audit(
                audit_log_repository,
                actor_id=submit_payload.actor_id,
                split=split,
                invoice_id=invoice.id,
                task_id=task.id,
                requested_member_id=submit_payload.member_id,
                requested_status=submit_payload.status,
                dispute_reason=submit_payload.dispute_reason,
                failure_reason="proxy confirmation is not allowed",
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="proxy confirmation is not allowed",
            )

        if submit_payload.member_id != split.member_id:
            record_split_confirmation_rejection_audit(
                audit_log_repository,
                actor_id=submit_payload.actor_id,
                split=split,
                invoice_id=invoice.id,
                task_id=task.id,
                requested_member_id=submit_payload.member_id,
                requested_status=submit_payload.status,
                dispute_reason=submit_payload.dispute_reason,
                failure_reason="member can only confirm own split",
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="member can only confirm own split",
            )

        previous_confirmation = confirmation_repository.get_by_split(split_id)
        confirmation = confirmation_repository.upsert_for_split(split_id, submit_payload)
        record_split_confirmation_audit(
            audit_log_repository,
            actor_id=submit_payload.actor_id,
            split=split,
            invoice_id=invoice.id,
            task_id=task.id,
            confirmation=confirmation,
            previous_confirmation=previous_confirmation,
            request_id=request_id,
        )
        return confirmation

    @router.get("/api/invoices/{invoice_id}/confirmations")
    def list_confirmations(
        invoice_id: str,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")

        task = task_repository.get(invoice.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        items = confirmation_repository.list_by_invoice(invoice_id)
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to view confirmations for this task",
        )
        if scope is TaskAccessScope.MEMBER:
            actor_id = identity.actor_id or ""
            items = [item for item in items if item.member_id == actor_id]
        return {"items": items}

    return router
