from fastapi import APIRouter, HTTPException, status

from trms_backend.domain.materials import MaterialRepository
from trms_backend.domain.invoices import InvoiceRepository
from trms_backend.domain.splits import (
    ExpenseSplitActorNotAllowedError,
    ExpenseSplitReplace,
    ExpenseSplitRepository,
    ensure_split_actor_allowed,
)
from trms_backend.domain.tasks import TaskRepository


def build_split_router(
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    split_repository: ExpenseSplitRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/invoices/{invoice_id}/splits", tags=["splits"])

    @router.put("")
    def replace_splits(invoice_id: str, payload: ExpenseSplitReplace):
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

        try:
            ensure_split_actor_allowed(
                actor_id=payload.actor_id,
                submitter_id=material.submitter_id,
                administrator_id=task.administrator_id,
                existing_member_ids={
                    split.member_id for split in split_repository.list_by_invoice(invoice_id)
                },
                target_member_ids={item.member_id for item in payload.items},
            )
        except ExpenseSplitActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

        unknown_members = [
            item.member_id for item in payload.items if item.member_id not in task.member_ids
        ]
        if unknown_members:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"split members are not in task: {', '.join(unknown_members)}",
            )

        total_cents = sum(item.amount_cents for item in payload.items)
        if total_cents != invoice.amount_cents:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="split amount total must equal invoice amount",
            )

        return {"items": split_repository.replace_for_invoice(invoice_id, payload.items)}

    @router.get("")
    def list_splits(invoice_id: str):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")
        return {"items": split_repository.list_by_invoice(invoice_id)}

    return router
