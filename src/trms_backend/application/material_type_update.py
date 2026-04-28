from __future__ import annotations

from trms_backend.domain.invoices import InvoiceRepository
from trms_backend.domain.materials import MaterialRecord, MaterialRepository, MaterialStatus, MaterialType
from trms_backend.domain.tasks import TaskRepository, TaskStatus


class MaterialTypeUpdateNotFoundError(ValueError):
    def __init__(self, material_id: str) -> None:
        self.material_id = material_id
        super().__init__(f"material not found: {material_id}")


class MaterialTypeUpdateTaskNotFoundError(ValueError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"task not found: {task_id}")


class MaterialTypeUpdateActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("only the material submitter can update material type")


class MaterialTypeUpdateConflictError(ValueError):
    pass


class MaterialTypeUpdateService:
    def __init__(
        self,
        task_repository: TaskRepository,
        material_repository: MaterialRepository,
        invoice_repository: InvoiceRepository,
    ) -> None:
        self._task_repository = task_repository
        self._material_repository = material_repository
        self._invoice_repository = invoice_repository

    def update_material_type(
        self,
        *,
        material_id: str,
        actor_id: str,
        material_type: MaterialType,
    ) -> MaterialRecord:
        material = self._material_repository.get(material_id)
        if material is None:
            raise MaterialTypeUpdateNotFoundError(material_id)
        if material.status is not MaterialStatus.ASSIGNED or material.task_id is None:
            raise MaterialTypeUpdateConflictError(
                "only assigned task materials can be updated"
            )
        if material.submitter_id is None or material.submitter_id != actor_id:
            raise MaterialTypeUpdateActorNotAllowedError()

        task = self._task_repository.get(material.task_id)
        if task is None:
            raise MaterialTypeUpdateTaskNotFoundError(material.task_id)
        if actor_id not in task.member_ids:
            raise MaterialTypeUpdateActorNotAllowedError()
        if task.status is not TaskStatus.OPEN:
            raise MaterialTypeUpdateConflictError(
                "members can only update material type while the task is open"
            )

        primary_invoice = self._invoice_repository.get_by_material(material_id)
        if primary_invoice is not None and material_type is not MaterialType.INVOICE:
            raise MaterialTypeUpdateConflictError(
                "material type cannot change away from invoice after invoice details exist"
            )

        supporting_invoices = self._invoice_repository.list_by_supporting_material(material_id)
        if supporting_invoices and material_type is MaterialType.INVOICE:
            raise MaterialTypeUpdateConflictError(
                "supporting material linked to invoices cannot be changed to invoice type"
            )

        updated = self._material_repository.update_material_type(
            material_id=material_id,
            material_type=material_type,
        )
        if updated is None:
            raise MaterialTypeUpdateConflictError(
                "only assigned task materials can be updated"
            )
        return updated
