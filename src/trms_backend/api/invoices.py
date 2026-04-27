from fastapi import APIRouter, HTTPException, status

from trms_backend.domain.invoice_validation import validate_invoice
from trms_backend.domain.invoices import (
    InvoiceManualEntryActorNotAllowedError,
    InvoiceRepository,
    ManualInvoiceEntry,
    ValidationRepository,
    ensure_manual_invoice_entry_actor_allowed,
)
from trms_backend.domain.materials import (
    MaterialRepository,
    MaterialStatus,
    MaterialType,
)
from trms_backend.domain.recognitions import RecognitionTaskRepository
from trms_backend.domain.tasks import (
    TaskExpenseTypeNotAllowedError,
    TaskRepository,
    ensure_task_allows_expense_type,
)


def build_invoice_router(
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    validation_repository: ValidationRepository,
    recognition_task_repository: RecognitionTaskRepository,
) -> APIRouter:
    router = APIRouter(tags=["invoices"])

    @router.post("/api/materials/{material_id}/invoice", status_code=status.HTTP_201_CREATED)
    def create_invoice(material_id: str, payload: ManualInvoiceEntry):
        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")
        if material.status is not MaterialStatus.ASSIGNED or material.task_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="material is not assigned to a task",
            )
        if material.material_type is not MaterialType.INVOICE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="invoice can only be created from invoice material",
            )

        task = task_repository.get(material.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        try:
            ensure_manual_invoice_entry_actor_allowed(
                actor_id=payload.actor_id,
                submitter_id=material.submitter_id,
                administrator_id=task.administrator_id,
            )
        except InvoiceManualEntryActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        try:
            ensure_task_allows_expense_type(task, payload.expense_type)
        except TaskExpenseTypeNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        invoice_data = payload.to_invoice_create()
        invoice = invoice_repository.upsert_for_material(
            material.task_id,
            material_id,
            invoice_data,
        )
        recognition_task_repository.apply_manual_corrections(
            material_id=material_id,
            actor_id=payload.actor_id,
            corrected_fields=invoice_data.model_dump(mode="json"),
            revalidation_field_names={
                "invoice_number",
                "issue_date",
                "transaction_time",
                "buyer_name",
                "tax_number",
                "seller_name",
                "amount_cents",
                "expense_type",
            },
        )
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

    @router.put("/api/invoices/{invoice_id}/supporting-materials/{material_id}")
    def attach_supporting_material(invoice_id: str, material_id: str):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")

        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")
        if material.status is not MaterialStatus.ASSIGNED or material.task_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="supporting material must be assigned to a task",
            )
        if material.task_id != invoice.task_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="supporting material belongs to a different task",
            )
        if material.material_type is MaterialType.INVOICE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="supporting material must not be invoice type",
            )

        invoice_repository.attach_supporting_material(invoice_id, material_id)
        return {"item": material}

    @router.get("/api/invoices/{invoice_id}/supporting-materials")
    def list_supporting_materials(invoice_id: str):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")

        items = []
        for link in invoice_repository.list_supporting_material_links(invoice_id):
            material = material_repository.get(link.material_id)
            if material is not None:
                items.append(material)
        return {"items": items}

    @router.delete("/api/invoices/{invoice_id}/supporting-materials/{material_id}")
    def detach_supporting_material(invoice_id: str, material_id: str):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")
        deleted = invoice_repository.detach_supporting_material(invoice_id, material_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="supporting material link not found",
            )
        return {"status": "deleted"}

    return router
