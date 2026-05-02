from __future__ import annotations

from dataclasses import dataclass

from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
from trms_backend.domain.auth import UserRole
from trms_backend.domain.confirmations import ConfirmationRepository
from trms_backend.domain.invoices import (
    InvoiceMemberSubmissionStatus,
    InvoiceRecord,
    InvoiceRepository,
    ValidationRepository,
)
from trms_backend.domain.materials import MaterialRecord, MaterialRepository
from trms_backend.domain.splits import ExpenseSplitRepository
from trms_backend.domain.tasks import ReimbursementTask, TaskStatus


@dataclass(frozen=True)
class MemberInvoiceDeletionResult:
    invoice: InvoiceRecord
    material: MaterialRecord


class MemberInvoiceDeletionNotFoundError(LookupError):
    def __init__(self, invoice_id: str) -> None:
        self.invoice_id = invoice_id
        super().__init__(f"invoice not found: {invoice_id}")


class MemberInvoiceDeletionMaterialNotFoundError(LookupError):
    def __init__(self, material_id: str) -> None:
        self.material_id = material_id
        super().__init__(f"invoice material not found: {material_id}")


class MemberInvoiceDeletionActorNotAllowedError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class MemberInvoiceDeletionConflictError(ValueError):
    pass


class MemberInvoiceDeletionService:
    def __init__(
        self,
        *,
        material_repository: MaterialRepository,
        invoice_repository: InvoiceRepository,
        split_repository: ExpenseSplitRepository,
        confirmation_repository: ConfirmationRepository,
        validation_repository: ValidationRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._material_repository = material_repository
        self._invoice_repository = invoice_repository
        self._split_repository = split_repository
        self._confirmation_repository = confirmation_repository
        self._validation_repository = validation_repository
        self._audit_log_repository = audit_log_repository

    def delete_invoice(
        self,
        *,
        task: ReimbursementTask,
        actor_id: str,
        actor_role: UserRole,
        invoice_id: str,
        request_id: str | None,
    ) -> MemberInvoiceDeletionResult:
        invoice = self._invoice_repository.get(invoice_id)
        if invoice is None:
            raise MemberInvoiceDeletionNotFoundError(invoice_id)
        if invoice.task_id != task.id:
            raise MemberInvoiceDeletionConflictError("invoice belongs to a different task")

        material = self._material_repository.get(invoice.material_id)
        if material is None:
            raise MemberInvoiceDeletionMaterialNotFoundError(invoice.material_id)

        self._validate_delete_allowed(
            task=task,
            actor_id=actor_id,
            actor_role=actor_role,
            invoice=invoice,
            material=material,
        )

        deleted_invoice = self._invoice_repository.delete_unsubmitted_invoice(invoice.id)
        if deleted_invoice is None:
            raise MemberInvoiceDeletionNotFoundError(invoice.id)
        deleted_material = self._material_repository.mark_deleted(material.id)
        if deleted_material is None:
            raise MemberInvoiceDeletionConflictError("invoice material is not assigned to a task")

        self._audit_log_repository.create(
            AuditLogCreate(
                actor_id=actor_id,
                object_type="invoice",
                object_id=invoice.id,
                action="delete_unsubmitted_invoice",
                result=AuditLogResult.SUCCEEDED,
                summary=f"delete unsubmitted invoice {invoice.id}",
                detail={
                    "material_id": material.id,
                    "invoice_number": invoice.invoice_number,
                    "member_submission_status": invoice.member_submission_status,
                    "split_count": len(self._split_repository.list_by_invoice(invoice.id)),
                    "confirmation_count": len(self._confirmation_repository.list_by_invoice(invoice.id)),
                    "validation_count": len(self._validation_repository.list_by_invoice(invoice.id)),
                    "material_original_filename": material.original_filename,
                },
                task_id=task.id,
                request_id=request_id,
            )
        )
        return MemberInvoiceDeletionResult(invoice=deleted_invoice, material=deleted_material)

    def _validate_delete_allowed(
        self,
        *,
        task: ReimbursementTask,
        actor_id: str,
        actor_role: UserRole,
        invoice: InvoiceRecord,
        material: MaterialRecord,
    ) -> None:
        if actor_role is not UserRole.MEMBER:
            raise MemberInvoiceDeletionActorNotAllowedError(
                "only members can delete unsubmitted invoices from the member workbench"
            )
        if task.status is not TaskStatus.OPEN:
            raise MemberInvoiceDeletionConflictError(
                "task is not open for member invoice deletion"
            )
        if material.submitter_id != actor_id:
            raise MemberInvoiceDeletionActorNotAllowedError(
                "actor can only delete invoices created from own materials"
            )
        if invoice.member_submission_status is not InvoiceMemberSubmissionStatus.UNSUBMITTED:
            raise MemberInvoiceDeletionConflictError(
                "submitted invoice cannot be deleted by member"
            )
        supporting_links = self._invoice_repository.list_supporting_material_links(invoice.id)
        if supporting_links:
            raise MemberInvoiceDeletionConflictError(
                "invoice with linked supporting materials cannot be deleted by member"
            )
