from __future__ import annotations

from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
from trms_backend.domain.exports import TaskExportJobRecord, TaskExportJobStatus


SYSTEM_EXPORT_ACTOR_ID = "system:export-worker"


def record_export_job_created_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    export_job: TaskExportJobRecord,
    request_id: str | None,
) -> None:
    audit_log_repository.create(
        AuditLogCreate(
            actor_id=actor_id,
            object_type="export_job",
            object_id=export_job.id,
            action="create_task_export_job",
            result=AuditLogResult.SUCCEEDED,
            summary=f"create export job {export_job.id}",
            detail={
                "kind": export_job.kind,
                "format": export_job.format,
                "requested_by": export_job.requested_by,
                "task_status_at_request": export_job.task_status_at_request,
                "task_data_version": export_job.task_data_version,
                "parameters": export_job.parameters,
            },
            task_id=export_job.task_id,
            request_id=request_id,
        )
    )


def record_export_job_terminal_status_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    export_job: TaskExportJobRecord,
    previous_status: TaskExportJobStatus,
    request_id: str | None,
) -> None:
    if export_job.status not in {TaskExportJobStatus.SUCCEEDED, TaskExportJobStatus.FAILED}:
        return

    audit_log_repository.create(
        AuditLogCreate(
            actor_id=actor_id,
            object_type="export_job",
            object_id=export_job.id,
            action=(
                "complete_task_export_job"
                if export_job.status is TaskExportJobStatus.SUCCEEDED
                else "fail_task_export_job"
            ),
            result=(
                AuditLogResult.SUCCEEDED
                if export_job.status is TaskExportJobStatus.SUCCEEDED
                else AuditLogResult.FAILED
            ),
            summary=f"{_summarize_terminal_status(export_job.status)} export job {export_job.id}",
            detail={
                "kind": export_job.kind,
                "format": export_job.format,
                "requested_by": export_job.requested_by,
                "previous_status": previous_status,
                "status": export_job.status,
                "failure_reason": export_job.failure_reason,
                "artifact": _serialize_artifact(export_job),
            },
            task_id=export_job.task_id,
            request_id=request_id,
        )
    )


def record_export_job_download_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    export_job: TaskExportJobRecord,
    request_id: str | None,
) -> None:
    audit_log_repository.create(
        AuditLogCreate(
            actor_id=actor_id,
            object_type="export_job",
            object_id=export_job.id,
            action="download_task_export_artifact",
            result=AuditLogResult.SUCCEEDED,
            summary=f"download export artifact for job {export_job.id}",
            detail={
                "kind": export_job.kind,
                "format": export_job.format,
                "requested_by": export_job.requested_by,
                "status": export_job.status,
                "artifact": _serialize_artifact(export_job),
            },
            task_id=export_job.task_id,
            request_id=request_id,
        )
    )


def _serialize_artifact(export_job: TaskExportJobRecord) -> dict[str, object] | None:
    if export_job.artifact is None:
        return None
    return {
        "filename": export_job.artifact.filename,
        "content_type": export_job.artifact.content_type,
        "size_bytes": export_job.artifact.size_bytes,
        "sha256": export_job.artifact.sha256,
    }


def _summarize_terminal_status(status: TaskExportJobStatus) -> str:
    if status is TaskExportJobStatus.SUCCEEDED:
        return "complete"
    return "fail"
