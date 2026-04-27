from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from trms_backend.domain.tasks import ReimbursementTask, ensure_task_has_member


class MaterialReminderCreate(BaseModel):
    administrator_id: str = Field(min_length=1)
    member_id: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def normalize_text(self) -> MaterialReminderCreate:
        self.administrator_id = self.administrator_id.strip()
        self.member_id = self.member_id.strip()
        self.content = self.content.strip()
        return self


class MaterialReminderRecord(BaseModel):
    id: str
    task_id: str
    administrator_id: str
    member_id: str
    content: str
    created_at: datetime


class TaskMaterialReminderActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to manage material reminders for this task")


class MaterialReminderRepository(Protocol):
    def create(self, *, task_id: str, data: MaterialReminderCreate) -> MaterialReminderRecord:
        raise NotImplementedError

    def list_by_task(self, task_id: str) -> list[MaterialReminderRecord]:
        raise NotImplementedError


def ensure_task_material_reminder_administrator(
    task: ReimbursementTask,
    *,
    actor_id: str,
) -> str:
    normalized_actor_id = actor_id.strip()
    if normalized_actor_id != task.administrator_id:
        raise TaskMaterialReminderActorNotAllowedError()
    return normalized_actor_id


def create_task_material_reminder(
    task: ReimbursementTask,
    *,
    reminder_repository: MaterialReminderRepository,
    payload: MaterialReminderCreate,
) -> MaterialReminderRecord:
    ensure_task_material_reminder_administrator(task, actor_id=payload.administrator_id)
    ensure_task_has_member(task, submitter_id=payload.member_id)
    return reminder_repository.create(task_id=task.id, data=payload)


def list_task_material_reminders(
    task: ReimbursementTask,
    *,
    reminder_repository: MaterialReminderRepository,
    actor_id: str,
) -> list[MaterialReminderRecord]:
    ensure_task_material_reminder_administrator(task, actor_id=actor_id)
    return reminder_repository.list_by_task(task.id)


class InMemoryMaterialReminderRepository:
    def __init__(self) -> None:
        self._reminders: dict[str, MaterialReminderRecord] = {}
        self._lock = RLock()

    def create(self, *, task_id: str, data: MaterialReminderCreate) -> MaterialReminderRecord:
        reminder = MaterialReminderRecord(
            id=str(uuid4()),
            task_id=task_id,
            administrator_id=data.administrator_id,
            member_id=data.member_id,
            content=data.content,
            created_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._reminders[reminder.id] = reminder
        return reminder

    def list_by_task(self, task_id: str) -> list[MaterialReminderRecord]:
        with self._lock:
            reminders = [
                reminder for reminder in self._reminders.values() if reminder.task_id == task_id
            ]
        return sorted(reminders, key=lambda reminder: reminder.created_at)
