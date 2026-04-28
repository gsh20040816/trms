from __future__ import annotations

from dataclasses import dataclass, field

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
from trms_backend.domain.recognitions import RecognitionTaskCreate, RecognitionTaskRepository
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
    ) -> None:
        self._task_repository = task_repository
        self._material_repository = material_repository
        self._material_file_storage = material_file_storage
        self._recognition_task_repository = recognition_task_repository

    def submit_to_task(
        self,
        *,
        task_id: str,
        submitter_id: str,
        channel: SubmissionChannel,
        material_type: MaterialType,
        files: list[SubmittedMaterialFile],
    ) -> MaterialSubmissionBatchResult:
        task = self._task_repository.get(task_id)
        if task is None:
            raise MaterialSubmissionTaskNotFoundError(task_id)
        if task.status is not TaskStatus.OPEN:
            raise MaterialSubmissionTaskNotOpenError(task_id)

        ensure_task_accepts_member_submission(task, submitter_id=submitter_id)
        return self._create_material_batch(
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

    def submit_pending_assignment(
        self,
        *,
        channel: SubmissionChannel,
        material_type: MaterialType,
        files: list[SubmittedMaterialFile],
        task_id_hint: str | None,
        submitter_id_hint: str | None,
    ) -> MaterialSubmissionBatchResult:
        return self._create_material_batch(
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
        return record
