from datetime import datetime, timezone

import trms_backend.__main__ as backend_main
from trms_backend.application.export_async_jobs import ExportAsyncJobProcessor
import trms_backend.application.recognition_async_jobs as recognition_async_jobs
from trms_backend.application.async_jobs import AsyncJobWorker, AsyncJobWorkerModeError
from trms_backend.application.recognition_async_jobs import RecognitionAsyncJobProcessor
from trms_backend.application.recognition_preparation import RecognitionTaskExecutionConflictError
from trms_backend.domain.audit_logs import InMemoryAuditLogRepository
from trms_backend.domain.exports import (
    StoredExportArtifactRecord,
    TaskExportJobRecord,
    TaskExportJobStatus,
    TaskExportVersionSnapshot,
)
from trms_backend.domain.recognitions import RecognitionTaskRecord, RecognitionTaskStatus
from trms_backend.runtime_config import load_runtime_config


class CountingProcessor:
    def __init__(self, job_type: str, processed_count: int) -> None:
        self.job_type = job_type
        self._processed_count = processed_count

    def run_once(self) -> int:
        return self._processed_count


def test_async_job_worker_run_once_aggregates_registered_processors():
    config = load_runtime_config(env={}, async_job_mode="worker")
    worker = AsyncJobWorker(
        config.async_jobs,
        processors=(
            CountingProcessor("recognition", 2),
            CountingProcessor("export", 1),
        ),
    )

    result = worker.run_once()

    assert worker.registered_job_types == ("recognition", "export")
    assert result.processed_counts == {"recognition": 2, "export": 1}
    assert result.total_processed == 3


def test_async_job_worker_rejects_in_process_mode():
    config = load_runtime_config(env={})
    worker = AsyncJobWorker(config.async_jobs)

    try:
        worker.run_once()
    except AsyncJobWorkerModeError as error:
        assert error.mode == "in_process"
    else:  # pragma: no cover - defensive branch
        raise AssertionError("expected worker mode validation to fail")


def test_backend_main_worker_once_uses_worker_entry(monkeypatch):
    config = load_runtime_config(env={}, async_job_mode="worker")
    calls: list[str] = []

    class FakeWorker:
        def run_once(self) -> None:
            calls.append("run_once")

    monkeypatch.setattr(backend_main, "load_runtime_config", lambda: config)
    monkeypatch.setattr(backend_main, "build_async_job_worker", lambda runtime_config: FakeWorker())

    exit_code = backend_main.main(["worker", "--once"])

    assert exit_code == 0
    assert calls == ["run_once"]


def test_backend_main_keeps_legacy_api_entrypoint(monkeypatch):
    config = load_runtime_config(env={})
    uvicorn_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        backend_main,
        "load_runtime_config",
        lambda api_host=None, api_port=None: config,
    )
    monkeypatch.setattr(
        backend_main.uvicorn,
        "run",
        lambda app, **kwargs: uvicorn_calls.append({"app": app, **kwargs}),
    )

    exit_code = backend_main.main(["--reload"])

    assert exit_code == 0
    assert uvicorn_calls == [
        {
            "app": "trms_backend.main:app",
            "host": config.api_host,
            "port": config.api_port,
            "reload": True,
        }
    ]


def test_recognition_async_processor_skips_duplicate_delivery_after_conflict(monkeypatch):
    refresh_calls: list[str] = []

    monkeypatch.setattr(
        recognition_async_jobs,
        "refresh_validations_for_material",
        lambda material_id, **_: refresh_calls.append(material_id),
    )

    now = datetime.now(timezone.utc)
    task = RecognitionTaskRecord(
        id="recognition-1",
        material_id="material-1",
        status=RecognitionTaskStatus.PENDING,
        created_at=now,
        updated_at=now,
    )

    class FakeRecognitionTaskRepository:
        def list_pending(self, *, limit: int):
            assert limit == 10
            return [task, task]

    class FakeRecognitionPreparationService:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def execute(self, recognition_task_id: str) -> RecognitionTaskRecord:
            self.calls.append(recognition_task_id)
            if len(self.calls) > 1:
                raise RecognitionTaskExecutionConflictError(
                    recognition_task_id,
                    RecognitionTaskStatus.SUCCEEDED,
                )
            return task.model_copy(update={"status": RecognitionTaskStatus.SUCCEEDED})

    preparation_service = FakeRecognitionPreparationService()
    processor = RecognitionAsyncJobProcessor(
        task_repository=object(),
        material_repository=object(),
        invoice_repository=object(),
        validation_repository=object(),
        recognition_task_repository=FakeRecognitionTaskRepository(),
        recognition_preparation_service=preparation_service,
    )

    processed_count = processor.run_once()

    assert processed_count == 1
    assert preparation_service.calls == ["recognition-1", "recognition-1"]
    assert refresh_calls == ["material-1"]


def test_export_async_processor_skips_duplicate_delivery_after_claim(monkeypatch):
    now = datetime.now(timezone.utc)
    job = TaskExportJobRecord(
        id="export-1",
        task_id="task-1",
        requested_by="admin-1",
        kind="reimbursement_summary",
        format="csv",
        status=TaskExportJobStatus.PENDING,
        parameters={},
        task_data_version="a" * 64,
        created_at=now,
        updated_at=now,
    )
    job_statuses = {job.id: TaskExportJobStatus.PENDING}
    built_artifacts: list[StoredExportArtifactRecord] = []

    class FakeExportJobRepository:
        def list_pending(self, *, limit: int):
            assert limit == 10
            return [job, job]

        def update_status(
            self,
            export_job_id: str,
            *,
            target_status: TaskExportJobStatus,
            failure_reason: str | None = None,
            artifact: StoredExportArtifactRecord | None = None,
            expected_current_status: TaskExportJobStatus | None = None,
        ):
            current = job_statuses.get(export_job_id)
            if current is None:
                return None
            if expected_current_status is not None and current is not expected_current_status:
                return None
            job_statuses[export_job_id] = target_status
            if artifact is not None:
                built_artifacts.append(artifact)
            return job.model_copy(
                update={
                    "status": target_status,
                    "failure_reason": failure_reason,
                    "artifact": artifact,
                }
            )

    processor = ExportAsyncJobProcessor(
        task_repository=type("TaskRepo", (), {"get": lambda self, task_id: object()})(),
        export_job_repository=FakeExportJobRepository(),
        invoice_repository=object(),
        material_repository=object(),
        material_file_storage=object(),
        validation_repository=object(),
        split_repository=object(),
        confirmation_repository=object(),
        audit_log_repository=InMemoryAuditLogRepository(),
    )
    monkeypatch.setattr(
        processor,
        "_build_current_export_snapshot",
        lambda task: TaskExportVersionSnapshot(
            task_status="ready_to_export",
            task_data_version="a" * 64,
        ),
    )
    monkeypatch.setattr(
        processor,
        "_build_export_artifact",
        lambda task, export_job: StoredExportArtifactRecord(
            storage_key="task-1/_exports/file.csv",
            filename="file.csv",
            content_type="text/csv",
            size_bytes=12,
            sha256="b" * 64,
        ),
    )

    processed_count = processor.run_once()

    assert processed_count == 1
    assert job_statuses == {"export-1": TaskExportJobStatus.SUCCEEDED}
    assert len(built_artifacts) == 1
