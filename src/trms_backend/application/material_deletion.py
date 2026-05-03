from __future__ import annotations

from trms_backend.domain.auth import UserRole
from trms_backend.domain.invoices import InvoiceMemberSubmissionStatus, InvoiceRepository
from trms_backend.domain.materials import MaterialRecord, MaterialRepository, MaterialStatus
from trms_backend.domain.tasks import TaskRepository, TaskStatus, is_task_administrator


class MaterialDeletionNotFoundError(LookupError):
    def __init__(self, material_id: str) -> None:
        self.material_id = material_id
        super().__init__(f"material not found: {material_id}")


class MaterialDeletionTaskNotFoundError(LookupError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"task not found: {task_id}")


class MaterialDeletionActorNotAllowedError(ValueError):
    def __init__(self, detail: str = "actor is not allowed to delete materials for this task") -> None:
        super().__init__(detail)


class MaterialDeletionConflictError(ValueError):
    pass


class MaterialDeletionService:
    def __init__(
        self,
        task_repository: TaskRepository,
        material_repository: MaterialRepository,
        invoice_repository: InvoiceRepository,
    ) -> None:
        self._task_repository = task_repository
        self._material_repository = material_repository
        self._invoice_repository = invoice_repository

    def mark_deleted(
        self,
        *,
        material_id: str,
        actor_id: str,
        actor_role: UserRole,
    ) -> MaterialRecord:
        material = self._material_repository.get(material_id)
        if material is None:
            raise MaterialDeletionNotFoundError(material_id)
        if material.status is MaterialStatus.DELETED:
            raise MaterialDeletionConflictError("material is already marked deleted")
        if material.status is not MaterialStatus.ASSIGNED or material.task_id is None:
            raise MaterialDeletionConflictError("material is not assigned to a task")

        task = self._task_repository.get(material.task_id)
        if task is None:
            raise MaterialDeletionTaskNotFoundError(material.task_id)
        primary_invoice = self._invoice_repository.get_by_material(material.id)
        supporting_invoices = self._invoice_repository.list_by_supporting_material(material.id)

        if actor_role in {UserRole.ADMIN, UserRole.SYSTEM_ADMIN}:
            if actor_role is UserRole.ADMIN and not is_task_administrator(task, actor_id=actor_id):
                raise MaterialDeletionActorNotAllowedError()
        elif actor_role is UserRole.MEMBER:
            self._validate_member_delete_allowed(
                task=task,
                actor_id=actor_id,
                material=material,
                primary_invoice=primary_invoice,
                supporting_invoices=supporting_invoices,
            )
        else:  # pragma: no cover - defensive branch
            raise MaterialDeletionActorNotAllowedError()

        if primary_invoice is not None:
            deleted_invoice = self._invoice_repository.delete_unsubmitted_invoice(primary_invoice.id)
            if deleted_invoice is None:
                raise MaterialDeletionConflictError("invoice material could not be deleted")
        for invoice in supporting_invoices:
            self._invoice_repository.detach_supporting_material(invoice.id, material.id)

        deleted = self._material_repository.mark_deleted(material.id)
        if deleted is None:
            raise MaterialDeletionConflictError("material is not assigned to a task")
        return deleted

    def _validate_member_delete_allowed(
        self,
        *,
        task,
        actor_id: str,
        material: MaterialRecord,
        primary_invoice,
        supporting_invoices,
    ) -> None:
        if task.status is not TaskStatus.OPEN:
            raise MaterialDeletionConflictError("task is not open for member material deletion")
        if material.submitter_id != actor_id:
            raise MaterialDeletionActorNotAllowedError(
                "actor can only delete own unsubmitted materials"
            )
        if (
            primary_invoice is not None
            and primary_invoice.member_submission_status is not InvoiceMemberSubmissionStatus.UNSUBMITTED
        ):
            raise MaterialDeletionConflictError("submitted material cannot be deleted by member")
        if any(
            invoice.member_submission_status is not InvoiceMemberSubmissionStatus.UNSUBMITTED
            for invoice in supporting_invoices
        ):
            raise MaterialDeletionConflictError("submitted material cannot be deleted by member")
