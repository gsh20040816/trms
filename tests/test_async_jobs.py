from datetime import datetime, timezone

import trms_backend.__main__ as backend_main
from trms_backend.application.export_async_jobs import ExportAsyncJobProcessor
from trms_backend.application.metrics import InMemoryMetricsCollector
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


def test_async_job_worker_run_once_emits_iteration_logs(monkeypatch):
    config = load_runtime_config(env={}, async_job_mode="worker")
    worker = AsyncJobWorker(
        config.async_jobs,
        processors=(CountingProcessor("recognition", 2),),
    )
    entries: list[str] = []
    monkeypatch.setattr(
        "trms_backend.application.async_jobs.LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: entries.append(f"{message} {payload}"),
            },
        )(),
    )

    worker.run_once()

    assert any("worker_poll_start" in entry for entry in entries)
    assert any("worker_poll_complete" in entry for entry in entries)
    assert any("'processed_counts': {'recognition': 2}" in entry for entry in entries)


def test_async_job_worker_run_forever_logs_idle_wait(monkeypatch):
    config = load_runtime_config(env={}, async_job_mode="worker")

    def stop_sleep(_seconds: float) -> None:
        raise StopIteration

    worker = AsyncJobWorker(
        config.async_jobs,
        processors=(CountingProcessor("recognition", 0),),
        sleep=stop_sleep,
    )
    entries: list[str] = []
    monkeypatch.setattr(
        "trms_backend.application.async_jobs.LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: entries.append(f"{message} {payload}"),
            },
        )(),
    )

    try:
        worker.run_forever()
    except StopIteration:
        pass
    else:  # pragma: no cover - defensive branch
        raise AssertionError("expected custom sleep to stop the worker loop")

    assert any("worker_idle_wait" in entry for entry in entries)
    assert any("'sleep_seconds': 5.0" in entry for entry in entries)


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
    config = load_runtime_config(
        env={},
        async_job_mode="worker",
        llm_api_key="sk-secret",
        llm_model="gpt-4.1-mini",
    )
    calls: list[str] = []

    class FakeWorker:
        mode = "worker"
        poll_interval_seconds = 5.0
        registered_job_types = ("recognition", "export")

        def run_once(self) -> None:
            calls.append("run_once")

    monkeypatch.setattr(backend_main, "load_runtime_config", lambda **_: config)
    monkeypatch.setattr(backend_main, "load_runtime_environment_variables", lambda: {})
    monkeypatch.setattr(backend_main, "build_async_job_worker", lambda runtime_config: FakeWorker())
    entries: list[str] = []
    monkeypatch.setattr(
        backend_main,
        "LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: entries.append(f"{message} {payload}"),
            },
        )(),
    )

    exit_code = backend_main.main(["worker", "--once"])

    assert exit_code == 0
    assert calls == ["run_once"]


def test_worker_entry_configures_info_logging(monkeypatch):
    basic_config_calls: list[dict[str, object]] = []
    config = load_runtime_config(env={}, async_job_mode="worker")

    class FakeWorker:
        mode = "worker"
        poll_interval_seconds = 5.0
        registered_job_types = ("recognition",)

        def run_once(self) -> None:
            return None

    monkeypatch.setattr(backend_main, "load_runtime_config", lambda **_: config)
    monkeypatch.setattr(backend_main, "load_runtime_environment_variables", lambda: {})
    monkeypatch.setattr(backend_main, "build_async_job_worker", lambda runtime_config: FakeWorker())
    monkeypatch.setattr(
        backend_main.logging,
        "basicConfig",
        lambda **kwargs: basic_config_calls.append(kwargs),
    )

    exit_code = backend_main.main(["worker", "--once"])

    assert exit_code == 0
    assert basic_config_calls == [
        {
            "level": backend_main.logging.INFO,
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "force": False,
        }
    ]


def test_backend_main_keeps_legacy_api_entrypoint(monkeypatch):
    config = load_runtime_config(env={})
    uvicorn_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        backend_main,
        "load_runtime_config",
        lambda api_host=None, api_port=None, env=None: config,
    )
    monkeypatch.setattr(backend_main, "load_runtime_environment_variables", lambda: {})
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
    metrics_collector = InMemoryMetricsCollector()
    processor = RecognitionAsyncJobProcessor(
        task_repository=object(),
        material_repository=object(),
        invoice_repository=object(),
        validation_repository=object(),
        recognition_task_repository=FakeRecognitionTaskRepository(),
        recognition_preparation_service=preparation_service,
        metrics_collector=metrics_collector,
    )

    processed_count = processor.run_once()

    assert processed_count == 1
    assert preparation_service.calls == ["recognition-1", "recognition-1"]
    assert refresh_calls == ["material-1"]
    assert metrics_collector.snapshot()["validation_results"] == {
        "failed_rule_counts": {},
        "pending_rule_counts": {},
    }


def test_recognition_async_processor_logs_processed_and_skipped_jobs(monkeypatch):
    refresh_calls: list[str] = []

    monkeypatch.setattr(
        recognition_async_jobs,
        "refresh_validations_for_material",
        lambda material_id, **_: refresh_calls.append(material_id),
    )

    now = datetime.now(timezone.utc)
    first_task = RecognitionTaskRecord(
        id="recognition-1",
        material_id="material-1",
        status=RecognitionTaskStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    second_task = first_task.model_copy(update={"id": "recognition-2", "material_id": "material-2"})

    class FakeRecognitionTaskRepository:
        def list_pending(self, *, limit: int):
            assert limit == 10
            return [first_task, second_task]

    class FakeRecognitionPreparationService:
        def execute(self, recognition_task_id: str) -> RecognitionTaskRecord:
            if recognition_task_id == "recognition-2":
                raise RecognitionTaskExecutionConflictError(
                    recognition_task_id,
                    RecognitionTaskStatus.SUCCEEDED,
                )
            return first_task.model_copy(update={"status": RecognitionTaskStatus.FAILED})

    entries: list[str] = []
    monkeypatch.setattr(
        recognition_async_jobs,
        "LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: entries.append(f"{message} {payload}"),
                "warning": lambda self, message, payload: entries.append(f"{message} {payload}"),
            },
        )(),
    )
    processor = RecognitionAsyncJobProcessor(
        task_repository=object(),
        material_repository=object(),
        invoice_repository=object(),
        validation_repository=object(),
        recognition_task_repository=FakeRecognitionTaskRepository(),
        recognition_preparation_service=FakeRecognitionPreparationService(),
        metrics_collector=InMemoryMetricsCollector(),
    )

    assert processor.run_once() == 1
    assert refresh_calls == ["material-1"]
    assert any("recognition_worker_job_processed" in entry for entry in entries)
    assert any("recognition_worker_job_skipped" in entry for entry in entries)
    assert any("recognition-1" in entry for entry in entries)
    assert any("material-1" in entry for entry in entries)
    assert any("recognition-2" in entry for entry in entries)


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

    metrics_collector = InMemoryMetricsCollector()
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
        metrics_collector=metrics_collector,
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
    assert metrics_collector.snapshot()["export_jobs"]["by_status"] == {
        "running": 1,
        "succeeded": 1,
    }


def test_export_async_processor_logs_failure_reason(monkeypatch):
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

    class FakeExportJobRepository:
        def list_pending(self, *, limit: int):
            assert limit == 10
            return [job]

        def update_status(
            self,
            export_job_id: str,
            *,
            target_status: TaskExportJobStatus,
            failure_reason: str | None = None,
            artifact: StoredExportArtifactRecord | None = None,
            expected_current_status: TaskExportJobStatus | None = None,
        ):
            return job.model_copy(
                update={
                    "status": target_status,
                    "failure_reason": failure_reason,
                    "artifact": artifact,
                }
            )

    entries: list[str] = []
    monkeypatch.setattr(
        "trms_backend.application.export_async_jobs.LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: entries.append(f"{message} {payload}"),
                "warning": lambda self, message, payload: entries.append(f"{message} {payload}"),
            },
        )(),
    )
    processor = ExportAsyncJobProcessor(
        task_repository=type("TaskRepo", (), {"get": lambda self, task_id: None})(),
        export_job_repository=FakeExportJobRepository(),
        invoice_repository=object(),
        material_repository=object(),
        material_file_storage=object(),
        validation_repository=object(),
        split_repository=object(),
        confirmation_repository=object(),
        audit_log_repository=InMemoryAuditLogRepository(),
        metrics_collector=InMemoryMetricsCollector(),
    )

    assert processor.run_once() == 1
    assert any("export_worker_job_failed" in entry for entry in entries)
    assert any("export-1" in entry for entry in entries)
    assert any("task not found" in entry for entry in entries)
