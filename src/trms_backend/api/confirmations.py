from fastapi import APIRouter, HTTPException, status

from trms_backend.domain.confirmations import ConfirmationRepository, ConfirmationSubmit
from trms_backend.domain.invoices import InvoiceRepository
from trms_backend.domain.splits import ExpenseSplitRepository


def build_confirmation_router(
    invoice_repository: InvoiceRepository,
    split_repository: ExpenseSplitRepository,
    confirmation_repository: ConfirmationRepository,
) -> APIRouter:
    router = APIRouter(tags=["confirmations"])

    @router.put("/api/splits/{split_id}/confirmation")
    def submit_confirmation(split_id: str, payload: ConfirmationSubmit):
        split = split_repository.get(split_id)
        if split is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="split not found")

        if payload.member_id != split.member_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="member can only confirm own split",
            )

        return confirmation_repository.upsert_for_split(split_id, payload)

    @router.get("/api/invoices/{invoice_id}/confirmations")
    def list_confirmations(invoice_id: str):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")
        return {"items": confirmation_repository.list_by_invoice(invoice_id)}

    return router

