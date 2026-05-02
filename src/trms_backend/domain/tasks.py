from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator
from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.auth import AuthenticatedUser
from trms_backend.domain.global_invoice_config import GlobalInvoiceConfig
from trms_backend.domain.invoices import (
    ExpenseType,
    InvoiceRecord,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from trms_backend.domain.splits import ExpenseSplitRecord


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

    @field_validator("member_ids", "fee_categories")
    @classmethod
    def reject_blank_items(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("list items must not be blank")
        return normalized

    @field_validator("fee_categories")
    @classmethod
    def validate_supported_fee_categories(cls, values: list[str]) -> list[str]:
        invalid_categories = [value for value in values if value not in _SUPPORTED_FEE_CATEGORIES]
        if invalid_categories:
            joined_categories = ", ".join(invalid_categories)
            raise ValueError(f"unsupported fee categories: {joined_categories}")
        return values

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
    project_info: str | None = None
    reimburser_info: str | None = None
    invoice_title: str | None = None
    tax_number: str | None = None

    @field_validator("project_info", "reimburser_info")
    @classmethod
    def normalize_optional_task_metadata(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

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
    project_info: str = ""
    reimburser_info: str = ""
    invoice_title: str = Field(min_length=1)
    tax_number: str = Field(min_length=1)


class TaskUpdateInput(BaseModel):
    competition_name: str = Field(min_length=1)
    competition_location: str = Field(min_length=1)
    competition_start_date: date
    competition_end_date: date
    deadline: datetime
    member_ids: list[str] = Field(min_length=1)
    fee_categories: list[str] = Field(min_length=1)
    project_info: str | None = None
    reimburser_info: str | None = None
    invoice_title: str = Field(min_length=1)
    tax_number: str = Field(min_length=1)

    @field_validator(
        "competition_name",
        "competition_location",
        "invoice_title",
        "tax_number",
    )
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("project_info", "reimburser_info")
    @classmethod
    def normalize_optional_task_metadata(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("member_ids", "fee_categories")
    @classmethod
    def reject_blank_items(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("list items must not be blank")
        return normalized

    @field_validator("fee_categories")
    @classmethod
    def validate_supported_fee_categories(cls, values: list[str]) -> list[str]:
        invalid_categories = [value for value in values if value not in _SUPPORTED_FEE_CATEGORIES]
        if invalid_categories:
            joined_categories = ", ".join(invalid_categories)
            raise ValueError(f"unsupported fee categories: {joined_categories}")
        return values

    @model_validator(mode="after")
    def validate_dates(self) -> "TaskUpdateInput":
        if self.competition_end_date < self.competition_start_date:
            raise ValueError("competition_end_date must not be earlier than competition_start_date")
        return self


class TaskStatusUpdate(BaseModel):
    target_status: TaskStatus


class TaskMembersUpdate(BaseModel):
    member_ids: list[str] = Field(min_length=1)

    @field_validator("member_ids")
    @classmethod
    def reject_blank_items(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("list items must not be blank")
        return normalized


class MissingTaskInvoiceConfigError(ValueError):
    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        joined_fields = ", ".join(missing_fields)
        super().__init__(f"missing invoice configuration fields: {joined_fields}")


class TaskPublishValidationError(ValueError):
    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        joined_fields = ", ".join(missing_fields)
        super().__init__(f"task is missing required publish fields: {joined_fields}")


class TaskExpenseTypeNotAllowedError(ValueError):
    def __init__(self, expense_type: ExpenseType, allowed_fee_categories: list[str]) -> None:
        self.expense_type = expense_type
        self.allowed_fee_categories = allowed_fee_categories
        allowed_categories = ", ".join(allowed_fee_categories)
        super().__init__(
            "invoice expense type "
            f"{expense_type.value} is not allowed for task; allowed fee categories: "
            f"{allowed_categories}"
        )


class TaskSubmissionDeadlinePassedError(ValueError):
    def __init__(self, deadline: datetime) -> None:
        self.deadline = deadline
        super().__init__("task deadline has passed for member material submission")


class TaskSubmitterNotMemberError(ValueError):
    def __init__(self, submitter_id: str) -> None:
        self.submitter_id = submitter_id
        super().__init__(f"submitter is not a member of the task: {submitter_id}")


class TaskReviewValidationError(ValueError):
    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__("task review is incomplete: " + "; ".join(reasons))


class TaskCompletionValidationError(ValueError):
    def __init__(self) -> None:
        super().__init__("task cannot transition to completed before export completion is recorded")


class ReimbursementTask(BaseModel):
    id: str
    status: TaskStatus
    competition_name: str
    competition_location: str
    competition_start_date: date
    competition_end_date: date
    deadline: datetime
    member_ids: list[str]
    member_summaries: list["TaskMemberSummary"] = Field(default_factory=list)
    fee_categories: list[str]
    administrator_id: str
    project_info: str
    reimburser_info: str
    invoice_title: str
    tax_number: str
    created_at: datetime
    updated_at: datetime


class TaskMemberSummary(BaseModel):
    member_id: str
    username: str | None = None
    display_name: str | None = None
    student_id: str | None = None


def build_task_member_summaries(
    member_ids: list[str],
    users: list[AuthenticatedUser],
) -> list[TaskMemberSummary]:
    users_by_member_identifier = {
        (user.member_code or user.actor_id): user
        for user in users
    }
    summaries: list[TaskMemberSummary] = []
    for member_id in member_ids:
        user = users_by_member_identifier.get(member_id)
        summaries.append(
            TaskMemberSummary(
                member_id=member_id,
                username=user.username if user else None,
                display_name=user.display_name if user else None,
                student_id=user.member_code if user else member_id,
            )
        )
    return summaries


class TaskRepository(Protocol):
    def create(self, data: TaskCreate) -> ReimbursementTask:
        raise NotImplementedError

    def get(self, task_id: str) -> ReimbursementTask | None:
        raise NotImplementedError

    def list(self) -> list[ReimbursementTask]:
        raise NotImplementedError

    def list_for_member(self, member_id: str) -> list[ReimbursementTask]:
        raise NotImplementedError

    def update_status(self, task_id: str, target_status: TaskStatus) -> ReimbursementTask | None:
        raise NotImplementedError

    def update_member_ids(self, task_id: str, member_ids: list[str]) -> ReimbursementTask | None:
        raise NotImplementedError

    def update_task(
        self,
        task_id: str,
        payload: TaskUpdateInput,
    ) -> ReimbursementTask | None:
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

    data = payload.model_dump(
        exclude={"project_info", "reimburser_info", "invoice_title", "tax_number"},
    )
    return TaskCreate(
        **data,
        project_info=(payload.project_info or "").strip(),
        reimburser_info=(payload.reimburser_info or "").strip(),
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


def ensure_task_can_publish(task: ReimbursementTask) -> None:
    missing_fields: list[str] = []
    if not _has_non_blank_items(task.member_ids):
        missing_fields.append("member_ids")
    if not _has_non_blank_items(task.fee_categories):
        missing_fields.append("fee_categories")
    if missing_fields:
        raise TaskPublishValidationError(missing_fields)


def _has_non_blank_items(values: list[str]) -> bool:
    return bool(values) and all(value.strip() for value in values)


def ensure_task_allows_expense_type(task: ReimbursementTask, expense_type: ExpenseType) -> None:
    if expense_type.value not in task.fee_categories:
        raise TaskExpenseTypeNotAllowedError(expense_type, task.fee_categories)


def ensure_task_accepts_member_submission(
    task: ReimbursementTask,
    *,
    submitter_id: str | None = None,
    now: datetime | None = None,
) -> None:
    if submitter_id is not None:
        ensure_task_has_member(task, submitter_id=submitter_id)
    if has_task_submission_deadline_passed(task, now=now):
        raise TaskSubmissionDeadlinePassedError(task.deadline)


def ensure_task_has_member(task: ReimbursementTask, *, submitter_id: str) -> None:
    if submitter_id not in task.member_ids:
        raise TaskSubmitterNotMemberError(submitter_id)


def has_task_submission_deadline_passed(
    task: ReimbursementTask,
    *,
    now: datetime | None = None,
) -> bool:
    deadline = task.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    reference_time = now or datetime.now(timezone.utc)
    return deadline <= reference_time


def ensure_task_can_enter_ready_to_export(
    invoices: list[InvoiceRecord],
    *,
    validations_by_invoice_id: dict[str, list[ValidationResult]],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
    pending_assignment_material_ids: list[str],
) -> None:
    invoices_missing_validations: list[str] = []
    invoices_with_blocker_issues: list[str] = []
    invoices_missing_splits: list[str] = []
    splits_missing_confirmation: list[str] = []
    splits_pending_confirmation: list[str] = []
    disputed_splits: list[str] = []

    for invoice in invoices:
        validations = validations_by_invoice_id.get(invoice.id, [])
        if not validations:
            invoices_missing_validations.append(invoice.id)
        elif any(
            result.severity == ValidationSeverity.BLOCKER
            and result.status in {ValidationStatus.FAILED, ValidationStatus.PENDING}
            for result in validations
        ):
            invoices_with_blocker_issues.append(invoice.id)

        splits = splits_by_invoice_id.get(invoice.id, [])
        if not splits:
            invoices_missing_splits.append(invoice.id)
            continue

        for split in splits:
            confirmation = confirmations_by_split_id.get(split.id)
            if confirmation is None:
                splits_missing_confirmation.append(split.id)
                continue
            if confirmation.status == ConfirmationStatus.PENDING:
                splits_pending_confirmation.append(split.id)
                continue
            if confirmation.status == ConfirmationStatus.DISPUTED:
                disputed_splits.append(split.id)

    reasons: list[str] = []
    if invoices_missing_validations:
        reasons.append(
            "missing invoice validations for invoices: "
            + ", ".join(invoices_missing_validations)
        )
    if invoices_with_blocker_issues:
        reasons.append(
            "blocker validations are not resolved for invoices: "
            + ", ".join(invoices_with_blocker_issues)
        )
    if invoices_missing_splits:
        reasons.append("missing expense splits for invoices: " + ", ".join(invoices_missing_splits))
    if splits_missing_confirmation:
        reasons.append(
            "member confirmations are still missing for splits: "
            + ", ".join(splits_missing_confirmation)
        )
    if splits_pending_confirmation:
        reasons.append(
            "member confirmations are still pending for splits: "
            + ", ".join(splits_pending_confirmation)
        )
    if disputed_splits:
        reasons.append("member confirmations are disputed for splits: " + ", ".join(disputed_splits))
    if pending_assignment_material_ids:
        reasons.append(
            "pending-assignment materials must be claimed before final confirmation "
            f"(count: {len(pending_assignment_material_ids)}, material_ids: "
            + ", ".join(pending_assignment_material_ids)
            + ")"
        )
    if reasons:
        raise TaskReviewValidationError(reasons)


def close_expired_open_tasks(
    repository: TaskRepository,
    *,
    now: datetime | None = None,
) -> list[ReimbursementTask]:
    closed_tasks: list[ReimbursementTask] = []
    reference_time = now or datetime.now(timezone.utc)
    for task in repository.list():
        if task.status != TaskStatus.OPEN:
            continue
        if not has_task_submission_deadline_passed(task, now=reference_time):
            continue
        updated = repository.update_status(task.id, TaskStatus.CLOSED)
        if updated is not None:
            closed_tasks.append(updated)
    return closed_tasks


_SUPPORTED_FEE_CATEGORIES = frozenset(expense_type.value for expense_type in ExpenseType)


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

    def update_member_ids(self, task_id: str, member_ids: list[str]) -> ReimbursementTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None

            updated = task.model_copy(
                update={
                    "member_ids": member_ids,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._tasks[task_id] = updated
            return updated

    def update_task(
        self,
        task_id: str,
        payload: TaskUpdateInput,
    ) -> ReimbursementTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None

            updated = task.model_copy(
                update={
                    **payload.model_dump(exclude_none=True),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._tasks[task_id] = updated
            return updated
