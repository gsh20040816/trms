from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field, field_validator, model_validator

from trms_backend.domain.tasks import ReimbursementTask, TaskStatus


class ExportArtifactKind(StrEnum):
    REIMBURSEMENT_SUMMARY = "reimbursement_summary"
    MEMBER_DETAILS = "member_details"
    INVOICE_DETAILS = "invoice_details"
    MISSING_MATERIALS = "missing_materials"
    FINANCE_DRAFT = "finance_draft"
    MERGED_PDF = "merged_pdf"


class ExportArtifactFormat(StrEnum):
    XLSX = "xlsx"
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"


class TaskExportCapability(BaseModel):
    kind: ExportArtifactKind
    formats: list[ExportArtifactFormat] = Field(min_length=1)
    implemented: bool = False


class TaskExportBoundary(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    current_task_status: TaskStatus
    export_allowed: bool
    blocking_reasons: list[str]
    execution_mode: str = Field(default="async_placeholder")
    supported_exports: list[TaskExportCapability]
    note: str = Field(
        default=(
            "export module boundary is established; real export jobs and files are not "
            "generated yet"
        )
    )


class TaskExportJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TaskExportJobRequest(BaseModel):
    actor_id: str = Field(min_length=1)
    kind: ExportArtifactKind
    format: ExportArtifactFormat
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_and_validate(self) -> TaskExportJobRequest:
        self.actor_id = self.actor_id.strip()
        _ensure_export_format_supported(self.kind, self.format)
        return self


class TaskExportJobCreate(BaseModel):
    requested_by: str = Field(min_length=1)
    kind: ExportArtifactKind
    format: ExportArtifactFormat
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_and_validate(self) -> TaskExportJobCreate:
        self.requested_by = self.requested_by.strip()
        _ensure_export_format_supported(self.kind, self.format)
        return self


class TaskExportJobRecord(BaseModel):
    id: str
    task_id: str
    requested_by: str
    kind: ExportArtifactKind
    format: ExportArtifactFormat
    status: TaskExportJobStatus
    parameters: dict[str, Any]
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TaskExportJobStatusUpdate(BaseModel):
    actor_id: str = Field(min_length=1)
    target_status: TaskExportJobStatus
    failure_reason: str | None = None

    @field_validator("failure_reason")
    @classmethod
    def normalize_failure_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("failure_reason must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_failure_reason(self) -> TaskExportJobStatusUpdate:
        self.actor_id = self.actor_id.strip()
        if self.target_status is TaskExportJobStatus.FAILED:
            if self.failure_reason is None:
                raise ValueError("failed export job requires failure_reason")
        elif self.failure_reason is not None:
            raise ValueError("failure_reason is only allowed when target_status is failed")
        return self


class TaskExportActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to manage exports for this task")


class TaskExportJobNotReadyError(ValueError):
    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__("task is not ready for export: " + "; ".join(reasons))


class TaskExportFormatNotSupportedError(ValueError):
    def __init__(
        self,
        kind: ExportArtifactKind,
        format: ExportArtifactFormat,
    ) -> None:
        super().__init__(f"export format {format.value} is not supported for {kind.value}")


class TaskExportJobStatusTransitionError(ValueError):
    def __init__(
        self,
        current_status: TaskExportJobStatus,
        target_status: TaskExportJobStatus,
    ) -> None:
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            "export job cannot transition from "
            f"{current_status.value} to {target_status.value}"
        )


class TaskExportJobRepository(Protocol):
    def create(
        self,
        *,
        task_id: str,
        data: TaskExportJobCreate,
    ) -> TaskExportJobRecord:
        raise NotImplementedError

    def get(self, export_job_id: str) -> TaskExportJobRecord | None:
        raise NotImplementedError

    def list_by_task(self, task_id: str) -> list[TaskExportJobRecord]:
        raise NotImplementedError

    def update_status(
        self,
        export_job_id: str,
        *,
        target_status: TaskExportJobStatus,
        failure_reason: str | None = None,
    ) -> TaskExportJobRecord | None:
        raise NotImplementedError


def build_task_export_boundary(
    task: ReimbursementTask,
    *,
    actor_id: str,
) -> TaskExportBoundary:
    normalized_actor_id = ensure_task_export_administrator(task, actor_id=actor_id)

    blocking_reasons: list[str] = []
    if task.status not in {TaskStatus.READY_TO_EXPORT, TaskStatus.COMPLETED}:
        blocking_reasons.append(
            "task must be ready_to_export or completed before real exports can be generated"
        )

    return TaskExportBoundary(
        task_id=task.id,
        administrator_id=normalized_actor_id,
        current_task_status=task.status,
        export_allowed=not blocking_reasons,
        blocking_reasons=blocking_reasons,
        supported_exports=_SUPPORTED_EXPORT_CAPABILITIES,
    )


def ensure_task_export_administrator(
    task: ReimbursementTask,
    *,
    actor_id: str,
) -> str:
    normalized_actor_id = actor_id.strip()
    if normalized_actor_id != task.administrator_id:
        raise TaskExportActorNotAllowedError()
    return normalized_actor_id


def create_task_export_job(
    task: ReimbursementTask,
    *,
    payload: TaskExportJobRequest,
    repository: TaskExportJobRepository,
) -> TaskExportJobRecord:
    boundary = build_task_export_boundary(task, actor_id=payload.actor_id)
    if not boundary.export_allowed:
        raise TaskExportJobNotReadyError(boundary.blocking_reasons)

    return repository.create(
        task_id=task.id,
        data=TaskExportJobCreate(
            requested_by=boundary.administrator_id,
            kind=payload.kind,
            format=payload.format,
            parameters=payload.parameters,
        ),
    )


def list_task_export_jobs(
    task: ReimbursementTask,
    *,
    actor_id: str,
    repository: TaskExportJobRepository,
) -> list[TaskExportJobRecord]:
    ensure_task_export_administrator(task, actor_id=actor_id)
    return repository.list_by_task(task.id)


def update_task_export_job_status(
    task: ReimbursementTask,
    *,
    export_job: TaskExportJobRecord,
    payload: TaskExportJobStatusUpdate,
    repository: TaskExportJobRepository,
) -> TaskExportJobRecord:
    ensure_task_export_administrator(task, actor_id=payload.actor_id)
    ensure_task_export_job_can_transition(export_job.status, payload.target_status)
    updated = repository.update_status(
        export_job.id,
        target_status=payload.target_status,
        failure_reason=payload.failure_reason,
    )
    if updated is None:
        raise ValueError("export job not found")
    return updated


def ensure_task_export_job_can_transition(
    current_status: TaskExportJobStatus,
    target_status: TaskExportJobStatus,
) -> None:
    if target_status not in _ALLOWED_EXPORT_JOB_TRANSITIONS[current_status]:
        raise TaskExportJobStatusTransitionError(current_status, target_status)


def _ensure_export_format_supported(
    kind: ExportArtifactKind,
    format: ExportArtifactFormat,
) -> None:
    supported_formats = _SUPPORTED_EXPORT_FORMATS_BY_KIND[kind]
    if format not in supported_formats:
        raise TaskExportFormatNotSupportedError(kind, format)


_SUPPORTED_EXPORT_CAPABILITIES = [
    TaskExportCapability(
        kind=ExportArtifactKind.REIMBURSEMENT_SUMMARY,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.CSV],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.MEMBER_DETAILS,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.CSV],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.INVOICE_DETAILS,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.CSV],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.MISSING_MATERIALS,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.CSV],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.FINANCE_DRAFT,
        formats=[ExportArtifactFormat.XLSX, ExportArtifactFormat.JSON],
    ),
    TaskExportCapability(
        kind=ExportArtifactKind.MERGED_PDF,
        formats=[ExportArtifactFormat.PDF],
    ),
]

_SUPPORTED_EXPORT_FORMATS_BY_KIND = {
    capability.kind: set(capability.formats) for capability in _SUPPORTED_EXPORT_CAPABILITIES
}

_ALLOWED_EXPORT_JOB_TRANSITIONS: dict[
    TaskExportJobStatus,
    set[TaskExportJobStatus],
] = {
    TaskExportJobStatus.PENDING: {
        TaskExportJobStatus.RUNNING,
        TaskExportJobStatus.SUCCEEDED,
        TaskExportJobStatus.FAILED,
    },
    TaskExportJobStatus.RUNNING: {
        TaskExportJobStatus.SUCCEEDED,
        TaskExportJobStatus.FAILED,
    },
    TaskExportJobStatus.SUCCEEDED: set(),
    TaskExportJobStatus.FAILED: set(),
}
