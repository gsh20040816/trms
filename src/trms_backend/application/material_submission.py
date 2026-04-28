from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from trms_backend.application.metrics import MetricsCollector, NoOpMetricsCollector
from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
from trms_backend.domain.materials import (
    MaterialCreate,
    MaterialFileStorage,
    MaterialRecord,
    MaterialRepository,
    MaterialStatus,
    MaterialType,
    MaterialUploadEmptyFileError,
    MaterialUploadMissingFilenameError,
    MaterialUploadTooLargeError,
    MaterialUploadUnsupportedContentTypeError,
    MaterialUploadValidationError,
    SubmissionChannel,
    validate_material_upload,
)
from trms_backend.domain.recognitions import (
    RecognitionTaskCreate,
    RecognitionTaskRepository,
    RecognitionTaskStatus,
)
from trms_backend.domain.tasks import (
    TaskRepository,
    TaskStatus,
    ensure_task_accepts_member_submission,
)

PENDING_ASSIGNMENT_STORAGE_NAMESPACE = "_pending_assignment"


@dataclass(frozen=True)
class SubmittedMaterialFile:
    original_filename: str | None
    content_type: str | None
    content: bytes


@dataclass(frozen=True)
class MaterialUploadFailure:
    original_filename: str | None
    error: MaterialUploadValidationError

    @property
    def error_code(self) -> str:
        if isinstance(self.error, MaterialUploadMissingFilenameError):
            return "missing_filename"
        if isinstance(self.error, MaterialUploadEmptyFileError):
            return "empty_file"
        if isinstance(self.error, MaterialUploadUnsupportedContentTypeError):
            return "unsupported_content_type"
        if isinstance(self.error, MaterialUploadTooLargeError):
            return "file_too_large"
        return "validation_error"

    @property
    def detail(self) -> str:
        return str(self.error)


@dataclass(frozen=True)
class MaterialSubmissionBatchResult:
    records: list[MaterialRecord] = field(default_factory=list)
    failures: list[MaterialUploadFailure] = field(default_factory=list)


class MaterialSubmissionTaskNotFoundError(LookupError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"task not found: {task_id}")


class MaterialSubmissionTaskNotOpenError(ValueError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"task is not open for material submission: {task_id}")


class MaterialSubmissionService:
    def __init__(
        self,
        task_repository: TaskRepository,
        material_repository: MaterialRepository,
        material_file_storage: MaterialFileStorage,
        recognition_task_repository: RecognitionTaskRepository,
        audit_log_repository: AuditLogRepository,
        metrics_collector: MetricsCollector | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._material_repository = material_repository
        self._material_file_storage = material_file_storage
        self._recognition_task_repository = recognition_task_repository
        self._audit_log_repository = audit_log_repository
        self._metrics_collector = metrics_collector or NoOpMetricsCollector()

    def read_material_content(self, *, storage_key: str) -> bytes:
        return self._material_file_storage.read(storage_key=storage_key)

    def submit_to_task(
        self,
        *,
        task_id: str,
        submitter_id: str,
        actor_id: str,
        channel: SubmissionChannel,
        material_type: MaterialType,
        files: list[SubmittedMaterialFile],
        request_id: str | None = None,
    ) -> MaterialSubmissionBatchResult:
        task = self._task_repository.get(task_id)
        if task is None:
            raise MaterialSubmissionTaskNotFoundError(task_id)
        if task.status is not TaskStatus.OPEN:
            raise MaterialSubmissionTaskNotOpenError(task_id)

        ensure_task_accepts_member_submission(task, submitter_id=submitter_id)
        result = self._create_material_batch(
            status=MaterialStatus.ASSIGNED,
            storage_task_id=task_id,
            submitter_id=submitter_id,
            task_id=task_id,
            task_id_hint=None,
            submitter_id_hint=None,
            channel=channel,
            material_type=material_type,
            files=files,
        )
        self._record_submission_audit_logs(
            actor_id=actor_id,
            channel=channel,
            material_type=material_type,
            result=result,
            task_id=task_id,
            submitter_id=submitter_id,
            task_id_hint=None,
            submitter_id_hint=None,
            request_id=request_id,
        )
        return result

    def submit_pending_assignment(
        self,
        *,
        actor_id: str,
        channel: SubmissionChannel,
        material_type: MaterialType,
        files: list[SubmittedMaterialFile],
        task_id_hint: str | None,
        submitter_id_hint: str | None,
        request_id: str | None = None,
    ) -> MaterialSubmissionBatchResult:
        result = self._create_material_batch(
            status=MaterialStatus.PENDING_ASSIGNMENT,
            storage_task_id=PENDING_ASSIGNMENT_STORAGE_NAMESPACE,
            submitter_id=None,
            task_id=None,
            task_id_hint=task_id_hint,
            submitter_id_hint=submitter_id_hint,
            channel=channel,
            material_type=material_type,
            files=files,
        )
        self._record_submission_audit_logs(
            actor_id=actor_id,
            channel=channel,
            material_type=material_type,
            result=result,
            task_id=None,
            submitter_id=None,
            task_id_hint=task_id_hint,
            submitter_id_hint=submitter_id_hint,
            request_id=request_id,
        )
        return result

    def _create_material_batch(
        self,
        *,
        status: MaterialStatus,
        storage_task_id: str,
        submitter_id: str | None,
        task_id: str | None,
        task_id_hint: str | None,
        submitter_id_hint: str | None,
        channel: SubmissionChannel,
        material_type: MaterialType,
        files: list[SubmittedMaterialFile],
    ) -> MaterialSubmissionBatchResult:
        validated_uploads, failures = self._validate_uploaded_files(files)
        records: list[MaterialRecord] = []
        for upload in validated_uploads:
            stored_file = self._material_file_storage.save(
                task_id=storage_task_id,
                original_filename=upload.original_filename or "",
                content_type=upload.content_type,
                content=upload.content,
            )
            records.append(
                self._create_material_with_recognition_placeholder(
                    MaterialCreate(
                        status=status,
                        task_id=task_id,
                        submitter_id=submitter_id,
                        task_id_hint=task_id_hint,
                        submitter_id_hint=submitter_id_hint,
                        channel=channel,
                        material_type=material_type,
                        storage_key=stored_file.storage_key,
                        original_filename=stored_file.original_filename,
                        content_type=stored_file.content_type,
                        size_bytes=stored_file.size_bytes,
                        sha256=stored_file.sha256,
                    )
                )
            )
            self._metrics_collector.record_material_upload_result(
                channel=channel,
                material_type=material_type,
                succeeded=True,
            )
        for failure in failures:
            self._metrics_collector.record_material_upload_result(
                channel=channel,
                material_type=material_type,
                succeeded=False,
                failure_code=failure.error_code,
            )
        return MaterialSubmissionBatchResult(records=records, failures=failures)

    def _validate_uploaded_files(
        self,
        files: list[SubmittedMaterialFile],
    ) -> tuple[list[SubmittedMaterialFile], list[MaterialUploadFailure]]:
        validated_uploads: list[SubmittedMaterialFile] = []
        failures: list[MaterialUploadFailure] = []
        for file in files:
            try:
                validate_material_upload(
                    original_filename=file.original_filename,
                    content_type=file.content_type,
                    content=file.content,
                )
            except MaterialUploadValidationError as error:
                failures.append(
                    MaterialUploadFailure(
                        original_filename=file.original_filename,
                        error=error,
                    )
                )
                continue
            validated_uploads.append(file)
        return validated_uploads, failures

    def _create_material_with_recognition_placeholder(self, data: MaterialCreate) -> MaterialRecord:
        record = self._material_repository.create(data)
        self._recognition_task_repository.create(RecognitionTaskCreate(material_id=record.id))
        self._metrics_collector.record_recognition_task_status(status=RecognitionTaskStatus.PENDING)
        return record

    def _record_submission_audit_logs(
        self,
        *,
        actor_id: str,
        channel: SubmissionChannel,
        material_type: MaterialType,
        result: MaterialSubmissionBatchResult,
        task_id: str | None,
        submitter_id: str | None,
        task_id_hint: str | None,
        submitter_id_hint: str | None,
        request_id: str | None,
    ) -> None:
        normalized_actor_id = _normalize_audit_actor_id(
            actor_id,
            fallback=f"channel:{channel.value}",
        )
        for record in result.records:
            self._audit_log_repository.create(
                AuditLogCreate(
                    actor_id=normalized_actor_id,
                    object_type="material",
                    object_id=record.id,
                    action="submit_material",
                    result=AuditLogResult.SUCCEEDED,
                    summary=(
                        f"submit material {record.id} via {record.channel.value} "
                        f"as {record.status.value}"
                    ),
                    detail={
                        "status": record.status,
                        "channel": record.channel,
                        "material_type": record.material_type,
                        "task_id": record.task_id,
                        "submitter_id": record.submitter_id,
                        "task_id_hint": record.task_id_hint,
                        "submitter_id_hint": record.submitter_id_hint,
                        "original_filename": record.original_filename,
                        "duplicate_of": record.duplicate_of,
                    },
                    task_id=record.task_id or record.task_id_hint,
                    request_id=request_id,
                )
            )

        submission_scope = task_id or task_id_hint or "pending-assignment"
        for index, failure in enumerate(result.failures, start=1):
            self._audit_log_repository.create(
                AuditLogCreate(
                    actor_id=normalized_actor_id,
                    object_type="material_submission",
                    object_id=_build_material_submission_failure_object_id(
                        request_id=request_id,
                        submission_scope=submission_scope,
                        index=index,
                    ),
                    action="submit_material",
                    result=AuditLogResult.REJECTED,
                    summary=(
                        f"reject material submission via {channel.value} "
                        f"for {submission_scope}"
                    ),
                    detail={
                        "channel": channel,
                        "material_type": material_type,
                        "task_id": task_id,
                        "submitter_id": submitter_id,
                        "task_id_hint": task_id_hint,
                        "submitter_id_hint": submitter_id_hint,
                        "original_filename": failure.original_filename,
                        "failure_code": failure.error_code,
                        "failure_detail": failure.detail,
                    },
                    task_id=task_id or task_id_hint,
                    request_id=request_id,
                )
            )


def _normalize_audit_actor_id(actor_id: str | None, *, fallback: str) -> str:
    normalized = (actor_id or "").strip()
    if normalized:
        return normalized[:128]
    return fallback[:128]


def _build_material_submission_failure_object_id(
    *,
    request_id: str | None,
    submission_scope: str,
    index: int,
) -> str:
    prefix = request_id or f"submission-{uuid4().hex}"
    return f"{prefix}:{submission_scope}:{index}"[:128]
