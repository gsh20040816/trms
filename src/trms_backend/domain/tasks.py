from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator
from trms_backend.domain.global_invoice_config import GlobalInvoiceConfig


class TaskStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    REVIEWING = "reviewing"
    READY_TO_EXPORT = "ready_to_export"
    COMPLETED = "completed"


class _TaskCreateBase(BaseModel):
    competition_name: str = Field(min_length=1)
    competition_location: str = Field(min_length=1)
    competition_start_date: date
    competition_end_date: date
    deadline: datetime
    member_ids: list[str] = Field(min_length=1)
    fee_categories: list[str] = Field(min_length=1)
    administrator_id: str = Field(min_length=1)
    project_info: str = Field(min_length=1)
    reimburser_info: str = Field(min_length=1)

    @field_validator("member_ids", "fee_categories")
    @classmethod
    def reject_blank_items(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("list items must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_dates(self) -> TaskCreate:
        if self.competition_end_date < self.competition_start_date:
            raise ValueError("competition_end_date must not be earlier than competition_start_date")

        deadline = self.deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= datetime.now(timezone.utc):
            raise ValueError("deadline must be in the future")

        return self


class TaskCreateInput(_TaskCreateBase):
    invoice_title: str | None = None
    tax_number: str | None = None

    @field_validator("invoice_title", "tax_number")
    @classmethod
    def reject_blank_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized


class TaskCreate(_TaskCreateBase):
    invoice_title: str = Field(min_length=1)
    tax_number: str = Field(min_length=1)


class TaskStatusUpdate(BaseModel):
    target_status: TaskStatus


class MissingTaskInvoiceConfigError(ValueError):
    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        joined_fields = ", ".join(missing_fields)
        super().__init__(f"missing invoice configuration fields: {joined_fields}")


class ReimbursementTask(BaseModel):
    id: str
    status: TaskStatus
    competition_name: str
    competition_location: str
    competition_start_date: date
    competition_end_date: date
    deadline: datetime
    member_ids: list[str]
    fee_categories: list[str]
    administrator_id: str
    project_info: str
    reimburser_info: str
    invoice_title: str
    tax_number: str
    created_at: datetime
    updated_at: datetime


class TaskRepository(Protocol):
    def create(self, data: TaskCreate) -> ReimbursementTask:
        raise NotImplementedError

    def get(self, task_id: str) -> ReimbursementTask | None:
        raise NotImplementedError

    def list(self) -> list[ReimbursementTask]:
        raise NotImplementedError

    def update_status(self, task_id: str, target_status: TaskStatus) -> ReimbursementTask | None:
        raise NotImplementedError


def resolve_task_create(
    payload: TaskCreateInput,
    global_invoice_config: GlobalInvoiceConfig | None,
) -> TaskCreate:
    invoice_title = payload.invoice_title
    if invoice_title is None and global_invoice_config is not None:
        invoice_title = global_invoice_config.invoice_title

    tax_number = payload.tax_number
    if tax_number is None and global_invoice_config is not None:
        tax_number = global_invoice_config.tax_number

    missing_fields: list[str] = []
    if invoice_title is None:
        missing_fields.append("invoice_title")
    if tax_number is None:
        missing_fields.append("tax_number")
    if missing_fields:
        raise MissingTaskInvoiceConfigError(missing_fields)

    data = payload.model_dump(exclude={"invoice_title", "tax_number"})
    return TaskCreate(
        **data,
        invoice_title=invoice_title,
        tax_number=tax_number,
    )


ALLOWED_STATUS_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.DRAFT: {TaskStatus.OPEN},
    TaskStatus.OPEN: {TaskStatus.DRAFT, TaskStatus.CLOSED},
    TaskStatus.CLOSED: {TaskStatus.OPEN, TaskStatus.REVIEWING},
    TaskStatus.REVIEWING: {TaskStatus.OPEN, TaskStatus.READY_TO_EXPORT},
    TaskStatus.READY_TO_EXPORT: {TaskStatus.COMPLETED},
    TaskStatus.COMPLETED: set(),
}


def can_transition(current_status: TaskStatus, target_status: TaskStatus) -> bool:
    return target_status in ALLOWED_STATUS_TRANSITIONS[current_status]


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, ReimbursementTask] = {}
        self._lock = RLock()

    def create(self, data: TaskCreate) -> ReimbursementTask:
        now = datetime.now(timezone.utc)
        task = ReimbursementTask(
            id=str(uuid4()),
            status=TaskStatus.DRAFT,
            created_at=now,
            updated_at=now,
            **data.model_dump(),
        )
        with self._lock:
            self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> ReimbursementTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list(self) -> list[ReimbursementTask]:
        with self._lock:
            return sorted(self._tasks.values(), key=lambda task: task.created_at)

    def update_status(self, task_id: str, target_status: TaskStatus) -> ReimbursementTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None

            updated = task.model_copy(
                update={
                    "status": target_status,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._tasks[task_id] = updated
            return updated
