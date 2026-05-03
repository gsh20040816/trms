from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from trms_backend.domain.auth import UserRole
from trms_backend.domain.materials import MaterialFileStorage, MaterialStatus
from trms_backend.domain.tasks import ReimbursementTask, TaskStatus, is_task_administrator
from trms_backend.infrastructure.database import session_scope
from trms_backend.infrastructure.models import (
    AuditLogRow,
    AutomaticReminderTaskRow,
    ConfirmationRow,
    ExportJobRow,
    ExpenseSplitRow,
    InvoiceRow,
    InvoiceSupportingMaterialLinkRow,
    MaterialReminderRow,
    MaterialRow,
    RecognitionTaskRow,
    TaskRow,
    ValidationResultRow,
)
from trms_backend.infrastructure.repositories import _task_from_row

LOGGER = logging.getLogger("trms_backend.task_deletion")


@dataclass(frozen=True)
class TaskDeletionResult:
    task: ReimbursementTask
    deleted_material_count: int
    deleted_pending_material_count: int
    deleted_invoice_count: int
    deleted_export_job_count: int


class TaskDeletionNotFoundError(LookupError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"task not found: {task_id}")


class TaskDeletionActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to delete this task")


class TaskDeletionService:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        material_file_storage: MaterialFileStorage,
    ) -> None:
        self._session_factory = session_factory
        self._material_file_storage = material_file_storage

    def delete_task(
        self,
        *,
        task_id: str,
        actor_id: str,
        actor_role: UserRole,
    ) -> TaskDeletionResult:
        deleted_storage_keys: list[str] = []
        deleted_export_storage_keys: list[str] = []

        with session_scope(self._session_factory) as session:
            task_row = session.get(TaskRow, task_id)
            if task_row is None:
                raise TaskDeletionNotFoundError(task_id)

            task = _task_from_row(task_row)
            self._ensure_actor_allowed(task=task, actor_id=actor_id, actor_role=actor_role)

            task_hint_candidates = {task.id}
            if task.email_submission_key is not None:
                task_hint_candidates.add(task.email_submission_key)

            assigned_material_rows = session.scalars(
                select(MaterialRow).where(MaterialRow.task_id == task.id)
            ).all()
            pending_material_rows = session.scalars(
                select(MaterialRow).where(
                    MaterialRow.status == MaterialStatus.PENDING_ASSIGNMENT.value,
                    MaterialRow.task_id_hint.in_(sorted(task_hint_candidates)),
                )
            ).all()

            all_material_rows = [*assigned_material_rows, *pending_material_rows]
            material_ids = [row.id for row in all_material_rows]
            deleted_storage_keys = [row.storage_key for row in all_material_rows]

            invoice_rows = session.scalars(
                select(InvoiceRow).where(InvoiceRow.task_id == task.id)
            ).all()
            invoice_ids = [row.id for row in invoice_rows]

            export_rows = session.scalars(
                select(ExportJobRow).where(ExportJobRow.task_id == task.id)
            ).all()
            for row in export_rows:
                raw_artifact = (row.parameters or {}).get("_artifact")
                if isinstance(raw_artifact, dict):
                    storage_key = raw_artifact.get("storage_key")
                    if isinstance(storage_key, str) and storage_key:
                        deleted_export_storage_keys.append(storage_key)

            session.execute(
                update(AuditLogRow)
                .where(AuditLogRow.task_id == task.id)
                .values(task_id=None)
            )

            session.execute(
                delete(MaterialReminderRow).where(MaterialReminderRow.task_id == task.id)
            )
            session.execute(
                delete(AutomaticReminderTaskRow).where(AutomaticReminderTaskRow.task_id == task.id)
            )
            session.execute(delete(ExportJobRow).where(ExportJobRow.task_id == task.id))

            if invoice_ids:
                session.execute(
                    delete(ConfirmationRow).where(
                        ConfirmationRow.split_id.in_(
                            select(ExpenseSplitRow.id).where(
                                ExpenseSplitRow.invoice_id.in_(invoice_ids)
                            )
                        )
                    )
                )
                session.execute(
                    delete(ExpenseSplitRow).where(ExpenseSplitRow.invoice_id.in_(invoice_ids))
                )
                session.execute(
                    delete(InvoiceSupportingMaterialLinkRow).where(
                        InvoiceSupportingMaterialLinkRow.invoice_id.in_(invoice_ids)
                    )
                )
                session.execute(
                    delete(ValidationResultRow).where(
                        ValidationResultRow.target_type == "invoice",
                        ValidationResultRow.target_id.in_(invoice_ids),
                    )
                )
                session.execute(delete(InvoiceRow).where(InvoiceRow.id.in_(invoice_ids)))

            if material_ids:
                session.execute(
                    delete(InvoiceSupportingMaterialLinkRow).where(
                        InvoiceSupportingMaterialLinkRow.material_id.in_(material_ids)
                    )
                )
                session.execute(
                    delete(RecognitionTaskRow).where(RecognitionTaskRow.material_id.in_(material_ids))
                )
                session.execute(delete(MaterialRow).where(MaterialRow.id.in_(material_ids)))

            session.delete(task_row)

        self._delete_storage_keys(deleted_storage_keys)
        self._delete_storage_keys(deleted_export_storage_keys)

        return TaskDeletionResult(
            task=task,
            deleted_material_count=len(assigned_material_rows),
            deleted_pending_material_count=len(pending_material_rows),
            deleted_invoice_count=len(invoice_rows),
            deleted_export_job_count=len(export_rows),
        )

    def _ensure_actor_allowed(
        self,
        *,
        task: ReimbursementTask,
        actor_id: str,
        actor_role: UserRole,
    ) -> None:
        if actor_role is UserRole.SYSTEM_ADMIN:
            return
        if actor_role is UserRole.ADMIN and is_task_administrator(task, actor_id=actor_id):
            return
        raise TaskDeletionActorNotAllowedError()

    def _delete_storage_keys(self, storage_keys: list[str]) -> None:
        for storage_key in storage_keys:
            try:
                self._material_file_storage.delete(storage_key=storage_key)
            except FileNotFoundError:
                continue
            except Exception:
                LOGGER.warning("task_delete_storage_cleanup_failed", extra={"storage_key": storage_key})
