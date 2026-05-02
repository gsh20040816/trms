from __future__ import annotations

from trms_backend.domain.invoices import InvoiceRepository
from trms_backend.domain.materials import MaterialRecord, MaterialRepository, MaterialStatus
from trms_backend.domain.tasks import TaskRepository, is_task_administrator


class MaterialDeletionNotFoundError(LookupError):
    def __init__(self, material_id: str) -> None:
        self.material_id = material_id
        super().__init__(f"material not found: {material_id}")


class MaterialDeletionTaskNotFoundError(LookupError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"task not found: {task_id}")


class MaterialDeletionActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to delete materials for this task")


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
        if not is_task_administrator(task, actor_id=actor_id):
            raise MaterialDeletionActorNotAllowedError()

        if self._invoice_repository.get_by_material(material.id) is not None:
            raise MaterialDeletionConflictError(
                "material is referenced by an invoice and cannot be marked deleted"
            )
        if self._invoice_repository.list_by_supporting_material(material.id):
            raise MaterialDeletionConflictError(
                "material is referenced by supporting invoice links and cannot be marked deleted"
            )

        deleted = self._material_repository.mark_deleted(material.id)
        if deleted is None:
            raise MaterialDeletionConflictError("material is not assigned to a task")
        return deleted
