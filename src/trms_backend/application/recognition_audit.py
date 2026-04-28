from __future__ import annotations

from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
from trms_backend.domain.recognitions import (
    RecognitionFieldCorrectionRecord,
    RecognitionFieldResult,
    RecognitionTaskRecord,
)


SYSTEM_RECOGNITION_ACTOR_ID = "system:recognition-worker"


def record_recognition_result_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    recognition_task: RecognitionTaskRecord,
    task_id: str | None,
    request_id: str | None,
) -> None:
    audit_log_repository.create(
        AuditLogCreate(
            actor_id=actor_id,
            object_type="recognition_task",
            object_id=recognition_task.id,
            action="record_recognition_result",
            result=(
                AuditLogResult.FAILED
                if recognition_task.failure is not None
                else AuditLogResult.SUCCEEDED
            ),
            summary=f"record recognition result for task {recognition_task.id}",
            detail={
                "material_id": recognition_task.material_id,
                "recognition_status": recognition_task.status,
                "recognized_field_count": len(recognition_task.recognized_fields),
                "recognized_fields": [
                    {
                        "field_name": field_name,
                        "source": field_result.source,
                        "status": field_result.status,
                        "confidence": field_result.confidence,
                    }
                    for field_name, field_result in recognition_task.recognized_fields.items()
                ],
                "pending_confirmation_fields": sorted(
                    field_name
                    for field_name, field_result in recognition_task.recognized_fields.items()
                    if field_result.status.value == "needs_confirmation"
                ),
                "failure_stage": (
                    recognition_task.failure.stage if recognition_task.failure is not None else None
                ),
                "failure_reason": (
                    recognition_task.failure.reason
                    if recognition_task.failure is not None
                    else None
                ),
            },
            task_id=task_id,
            request_id=request_id,
        )
    )


def record_manual_recognition_corrections_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    recognition_task: RecognitionTaskRecord,
    task_id: str | None,
    request_id: str | None,
    corrections: list[RecognitionFieldCorrectionRecord],
) -> None:
    if not corrections:
        return

    audit_log_repository.create(
        AuditLogCreate(
            actor_id=actor_id,
            object_type="recognition_task",
            object_id=recognition_task.id,
            action="apply_manual_recognition_corrections",
            result=AuditLogResult.SUCCEEDED,
            summary=f"apply manual recognition corrections for task {recognition_task.id}",
            detail={
                "material_id": recognition_task.material_id,
                "correction_count": len(corrections),
                "changed_fields": [
                    {
                        "field_name": correction.field_name,
                        "before": _serialize_field_result(correction.before),
                        "after": _serialize_field_result(correction.after),
                        "revalidation_status": correction.revalidation_status,
                        "corrected_at": correction.corrected_at,
                    }
                    for correction in corrections
                ],
            },
            task_id=task_id,
            request_id=request_id,
        )
    )


def _serialize_field_result(field_result: RecognitionFieldResult | None) -> dict[str, object] | None:
    if field_result is None:
        return None
    return {
        "value": field_result.value,
        "source": field_result.source,
        "status": field_result.status,
        "confidence": field_result.confidence,
        "updated_at": field_result.updated_at,
    }
