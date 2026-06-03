from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from trms_backend.domain.tasks import (
    ReimbursementTask,
    ensure_task_administrator,
    ensure_task_has_member,
)


class MaterialReminderEmailDeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class MaterialReminderCreate(BaseModel):
    administrator_id: str = Field(min_length=1)
    member_id: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=2000)
    email_recipient: str | None = Field(default=None, max_length=320)
    email_subject: str | None = Field(default=None, max_length=255)
    email_body: str | None = Field(default=None, max_length=8000)
    email_delivery_status: MaterialReminderEmailDeliveryStatus = (
        MaterialReminderEmailDeliveryStatus.PENDING
    )
    email_failure_reason: str | None = Field(default=None, max_length=1000)
    email_sent_at: datetime | None = None

    @model_validator(mode="after")
    def normalize_text(self) -> MaterialReminderCreate:
        self.administrator_id = self.administrator_id.strip()
        self.member_id = self.member_id.strip()
        self.content = self.content.strip()
        self.email_recipient = _normalize_optional_text(self.email_recipient)
        self.email_subject = _normalize_optional_text(self.email_subject)
        self.email_body = _normalize_optional_text(self.email_body)
        self.email_failure_reason = _normalize_optional_text(self.email_failure_reason)
        return self


class MaterialReminderRecord(BaseModel):
    id: str
    task_id: str
    administrator_id: str
    member_id: str
    content: str
    email_recipient: str | None = None
    email_subject: str | None = None
    email_body: str | None = None
    email_delivery_status: MaterialReminderEmailDeliveryStatus | None = None
    email_failure_reason: str | None = None
    email_sent_at: datetime | None = None
    created_at: datetime


class TaskMaterialReminderActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to manage material reminders for this task")


class MaterialReminderRepository(Protocol):
    def create(self, *, task_id: str, data: MaterialReminderCreate) -> MaterialReminderRecord:
        raise NotImplementedError

    def update_email_delivery(
        self,
        reminder_id: str,
        *,
        status: MaterialReminderEmailDeliveryStatus,
        sent_at: datetime | None,
        failure_reason: str | None,
    ) -> MaterialReminderRecord | None:
        raise NotImplementedError

    def list_by_task(self, task_id: str) -> list[MaterialReminderRecord]:
        raise NotImplementedError


def ensure_task_material_reminder_administrator(
    task: ReimbursementTask,
    *,
    actor_id: str,
) -> str:
    return ensure_task_administrator(
        task,
        actor_id=actor_id,
        error_type=TaskMaterialReminderActorNotAllowedError,
    )


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
            email_recipient=data.email_recipient,
            email_subject=data.email_subject,
            email_body=data.email_body,
            email_delivery_status=data.email_delivery_status,
            email_failure_reason=data.email_failure_reason,
            email_sent_at=data.email_sent_at,
            created_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._reminders[reminder.id] = reminder
        return reminder

    def update_email_delivery(
        self,
        reminder_id: str,
        *,
        status: MaterialReminderEmailDeliveryStatus,
        sent_at: datetime | None,
        failure_reason: str | None,
    ) -> MaterialReminderRecord | None:
        with self._lock:
            reminder = self._reminders.get(reminder_id)
            if reminder is None:
                return None
            updated = reminder.model_copy(
                update={
                    "email_delivery_status": status,
                    "email_sent_at": sent_at,
                    "email_failure_reason": failure_reason,
                }
            )
            self._reminders[reminder_id] = updated
            return updated

    def list_by_task(self, task_id: str) -> list[MaterialReminderRecord]:
        with self._lock:
            reminders = [
                reminder for reminder in self._reminders.values() if reminder.task_id == task_id
            ]
        return sorted(reminders, key=lambda reminder: reminder.created_at)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
