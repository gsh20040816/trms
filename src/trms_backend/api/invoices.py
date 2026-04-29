from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError, model_validator

from trms_backend.api.error_responses import ensure_request_id
from trms_backend.api.invoice_validation_refresh import refresh_invoice_validations
from trms_backend.api.request_identity import (
    RequestIdentity,
    build_optional_request_identity_dependency,
)
from trms_backend.api.request_identity_http import resolve_required_actor_request_field
from trms_backend.api.request_task_access import TaskAccessScope, resolve_task_access_scope
from trms_backend.application.metrics import MetricsCollector, NoOpMetricsCollector
from trms_backend.application.recognition_audit import record_manual_recognition_corrections_audit
from trms_backend.application.supporting_material_auto_link import (
    SupportingMaterialAutoLinkService,
)
from trms_backend.domain.audit_logs import AuditLogRepository
from trms_backend.domain.auth import AuthRepository
from trms_backend.domain.invoice_validation import validate_invoice
from trms_backend.domain.invoices import (
    ExpenseType,
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


class ManualInvoiceEntryRequest(BaseModel):
    actor_id: str | None = None
    invoice_number: str = Field(min_length=1)
    issue_date: date | None = None
    transaction_time: datetime | None = None
    buyer_name: str = Field(min_length=1)
    tax_number: str = Field(min_length=1)
    seller_name: str | None = None
    amount_cents: int = Field(gt=0)
    expense_type: ExpenseType

    @model_validator(mode="after")
    def normalize_text(self) -> "ManualInvoiceEntryRequest":
        if self.actor_id is not None:
            self.actor_id = self.actor_id.strip() or None
        self.invoice_number = self.invoice_number.strip()
        self.buyer_name = self.buyer_name.strip()
        self.tax_number = self.tax_number.strip()
        if self.seller_name is not None:
            self.seller_name = self.seller_name.strip() or None
        return self

    def to_domain(self, *, actor_id: str) -> ManualInvoiceEntry:
        return ManualInvoiceEntry.model_validate(
            {
                "actor_id": actor_id,
                "invoice_number": self.invoice_number,
                "issue_date": self.issue_date,
                "transaction_time": self.transaction_time,
                "buyer_name": self.buyer_name,
                "tax_number": self.tax_number,
                "seller_name": self.seller_name,
                "amount_cents": self.amount_cents,
                "expense_type": self.expense_type,
            }
        )


def build_invoice_router(
    auth_repository: AuthRepository,
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    validation_repository: ValidationRepository,
    recognition_task_repository: RecognitionTaskRepository,
    audit_log_repository: AuditLogRepository,
    metrics_collector: MetricsCollector | None = None,
) -> APIRouter:
    router = APIRouter(tags=["invoices"])
    optional_request_identity = build_optional_request_identity_dependency(auth_repository)
    metrics = metrics_collector or NoOpMetricsCollector()
    supporting_material_auto_link_service = SupportingMaterialAutoLinkService(
        material_repository=material_repository,
        invoice_repository=invoice_repository,
    )

    def load_supporting_materials(invoice_id: str) -> list:
        supporting_materials = []
        for link in invoice_repository.list_supporting_material_links(invoice_id):
            material = material_repository.get(link.material_id)
            if material is not None:
                supporting_materials.append(material)
        return supporting_materials

    def load_supporting_material_recognitions(supporting_materials: list) -> dict[str, object | None]:
        return {
            material.id: recognition_task_repository.get_latest_effective_by_material(material.id)
            for material in supporting_materials
        }

    @router.post("/api/materials/{material_id}/invoice", status_code=status.HTTP_201_CREATED)
    def create_invoice(
        material_id: str,
        request: Request,
        payload: ManualInvoiceEntryRequest,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
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
        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            payload.actor_id,
            field_name="actor_id",
        )
        try:
            manual_entry = payload.to_domain(actor_id=resolved_actor_id)
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        try:
            ensure_manual_invoice_entry_actor_allowed(
                actor_id=manual_entry.actor_id,
                submitter_id=material.submitter_id,
                administrator_id=task.administrator_id,
            )
        except InvoiceManualEntryActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        try:
            ensure_task_allows_expense_type(task, manual_entry.expense_type)
        except TaskExpenseTypeNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        invoice_data = manual_entry.to_invoice_create()
        latest_effective_recognition = recognition_task_repository.get_latest_effective_by_material(
            material_id
        )
        existing_recognition_tasks = recognition_task_repository.list_by_material(material_id)
        latest_target_task = existing_recognition_tasks[-1] if existing_recognition_tasks else None
        previous_correction_ids = (
            {item.id for item in latest_target_task.manual_corrections}
            if latest_target_task is not None
            else set()
        )
        invoice = invoice_repository.upsert_for_material(
            material.task_id,
            material_id,
            invoice_data,
        )
        supporting_material_auto_link_service.auto_link_for_invoice(invoice)
        supporting_materials = load_supporting_materials(invoice.id)
        supporting_material_recognitions = load_supporting_material_recognitions(
            supporting_materials
        )
        updated_recognition_task = recognition_task_repository.apply_manual_corrections(
            material_id=material_id,
            actor_id=manual_entry.actor_id,
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
        new_corrections = [
            item
            for item in updated_recognition_task.manual_corrections
            if item.id not in previous_correction_ids
        ]
        record_manual_recognition_corrections_audit(
            audit_log_repository,
            actor_id=manual_entry.actor_id,
            recognition_task=updated_recognition_task,
            task_id=material.task_id,
            request_id=ensure_request_id(request),
            corrections=new_corrections,
        )
        validations = validation_repository.replace_for_invoice(
            invoice.id,
            validate_invoice(
                invoice,
                task,
                invoice_repository.find_duplicate_invoice_id(
                    invoice.task_id,
                    invoice.invoice_number,
                    invoice.id,
                ),
                latest_effective_recognition,
                supporting_materials=supporting_materials,
                supporting_material_recognitions=supporting_material_recognitions,
            ),
        )
        metrics.record_validation_results(results=validations)
        return {"invoice": invoice, "validations": validations}

    @router.get("/api/tasks/{task_id}/invoices")
    def list_invoices(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        items = invoice_repository.list_by_task(task_id)
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to view invoices for this task",
        )
        if scope is TaskAccessScope.MEMBER:
            actor_id = identity.actor_id or ""
            visible_material_ids = {
                material.id
                for material in material_repository.list_by_task(task_id)
                if material.submitter_id == actor_id
            }
            items = [item for item in items if item.material_id in visible_material_ids]
        return {"items": items}

    @router.get("/api/invoices/{invoice_id}/validations")
    def list_invoice_validations(
        invoice_id: str,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")

        task = task_repository.get(invoice.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to view invoice validations for this task",
        )
        if scope is TaskAccessScope.MEMBER:
            material = material_repository.get(invoice.material_id)
            if material is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="invoice material not found",
                )
            if material.submitter_id != identity.actor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="actor is not allowed to view invoice validations for this task",
                )
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
        refresh_invoice_validations(
            invoice_id,
            task_repository=task_repository,
            material_repository=material_repository,
            invoice_repository=invoice_repository,
            validation_repository=validation_repository,
            recognition_task_repository=recognition_task_repository,
            metrics_collector=metrics,
        )
        return {"item": material}

    @router.get("/api/invoices/{invoice_id}/supporting-materials")
    def list_supporting_materials(
        invoice_id: str,
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
        invoice = invoice_repository.get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice not found")

        task = task_repository.get(invoice.task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to view supporting materials for this task",
        )

        items = []
        for link in invoice_repository.list_supporting_material_links(invoice_id):
            material = material_repository.get(link.material_id)
            if material is not None:
                if scope is TaskAccessScope.MEMBER and material.submitter_id != identity.actor_id:
                    continue
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
        refresh_invoice_validations(
            invoice_id,
            task_repository=task_repository,
            material_repository=material_repository,
            invoice_repository=invoice_repository,
            validation_repository=validation_repository,
            recognition_task_repository=recognition_task_repository,
            metrics_collector=metrics,
        )
        return {"status": "deleted"}

    return router
