from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

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


class TaskExportActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to manage exports for this task")


def build_task_export_boundary(
    task: ReimbursementTask,
    *,
    actor_id: str,
) -> TaskExportBoundary:
    normalized_actor_id = actor_id.strip()
    if normalized_actor_id != task.administrator_id:
        raise TaskExportActorNotAllowedError()

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
