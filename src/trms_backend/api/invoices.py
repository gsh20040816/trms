from fastapi import APIRouter, HTTPException, status

from trms_backend.domain.invoice_validation import validate_invoice
from trms_backend.domain.invoices import InvoiceCreate, InvoiceRepository, ValidationRepository
from trms_backend.domain.materials import MaterialRepository
from trms_backend.domain.tasks import TaskRepository


def build_invoice_router(
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    validation_repository: ValidationRepository,
) -> APIRouter:
    router = APIRouter(tags=["invoices"])

    @router.post("/api/materials/{material_id}/invoice", status_code=status.HTTP_201_CREATED)
    def create_invoice(material_id: str, payload: InvoiceCreate):
        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")

        task = task_repository.get(material.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoice = invoice_repository.create(material.task_id, material_id, payload)
        duplicate_invoice_id = invoice_repository.find_duplicate_invoice_id(
            invoice.task_id,
            invoice.invoice_number,
            invoice.id,
        )
        validations = validation_repository.replace_for_invoice(
            invoice.id,
            validate_invoice(invoice, task, duplicate_invoice_id),
        )
        return {"invoice": invoice, "validations": validations}

    @router.get("/api/tasks/{task_id}/invoices")
    def list_invoices(task_id: str):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"items": invoice_repository.list_by_task(task_id)}

    @router.get("/api/invoices/{invoice_id}/validations")
    def list_invoice_validations(invoice_id: str):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")
        return {"items": validation_repository.list_by_invoice(invoice_id)}

    return router

