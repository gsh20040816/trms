from fastapi import APIRouter, HTTPException, status

from trms_backend.domain.invoices import InvoiceRepository
from trms_backend.domain.splits import ExpenseSplitReplace, ExpenseSplitRepository
from trms_backend.domain.tasks import TaskRepository


def build_split_router(
    task_repository: TaskRepository,
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

