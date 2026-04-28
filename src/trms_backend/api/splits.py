from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

from trms_backend.api.request_identity import (
    RequestIdentity,
    build_optional_request_identity_dependency,
)
from trms_backend.api.request_identity_http import resolve_required_actor_request_field
from trms_backend.api.request_task_access import TaskAccessScope, resolve_task_access_scope
from trms_backend.domain.auth import AuthRepository

from trms_backend.domain.materials import MaterialRepository
from trms_backend.domain.invoices import InvoiceRepository
from trms_backend.domain.splits import (
    ExpenseSplitActorNotAllowedError,
    ExpenseSplitItem,
    ExpenseSplitReplace,
    ExpenseSplitRepository,
    ensure_split_actor_allowed,
)
from trms_backend.domain.tasks import TaskRepository


class ExpenseSplitReplaceRequest(BaseModel):
    actor_id: str | None = None
    items: list[ExpenseSplitItem]

    def to_domain(self, *, actor_id: str) -> ExpenseSplitReplace:
        return ExpenseSplitReplace.model_validate(
            {
                "actor_id": actor_id,
                "items": [item.model_dump(mode="json") for item in self.items],
            }
        )


def build_split_router(
    auth_repository: AuthRepository,
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    split_repository: ExpenseSplitRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/invoices/{invoice_id}/splits", tags=["splits"])
    optional_request_identity = build_optional_request_identity_dependency(auth_repository)

    @router.put("")
    def replace_splits(
        invoice_id: str,
        payload: ExpenseSplitReplaceRequest,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")

        task = task_repository.get(invoice.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        material = material_repository.get(invoice.material_id)
        if material is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="invoice material not found",
            )

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            payload.actor_id,
            field_name="actor_id",
        )
        try:
            replace_payload = payload.to_domain(actor_id=resolved_actor_id)
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        try:
            ensure_split_actor_allowed(
                actor_id=replace_payload.actor_id,
                submitter_id=material.submitter_id,
                administrator_id=task.administrator_id,
                existing_member_ids={
                    split.member_id for split in split_repository.list_by_invoice(invoice_id)
                },
                target_member_ids={item.member_id for item in replace_payload.items},
            )
        except ExpenseSplitActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

        unknown_members = [
            item.member_id
            for item in replace_payload.items
            if item.member_id not in task.member_ids
        ]
        if unknown_members:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"split members are not in task: {', '.join(unknown_members)}",
            )

        total_cents = sum(item.amount_cents for item in replace_payload.items)
        if total_cents != invoice.amount_cents:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="split amount total must equal invoice amount",
            )

        return {"items": split_repository.replace_for_invoice(invoice_id, replace_payload.items)}

    @router.get("")
    def list_splits(
        invoice_id: str,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")

        task = task_repository.get(invoice.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        items = split_repository.list_by_invoice(invoice_id)
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to view expense splits for this task",
        )
        if scope is TaskAccessScope.MEMBER:
            actor_id = identity.actor_id or ""
            items = [item for item in items if item.member_id == actor_id]
        return {"items": items}

    return router
