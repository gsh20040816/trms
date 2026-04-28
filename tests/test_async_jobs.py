import trms_backend.__main__ as backend_main
from trms_backend.application.async_jobs import AsyncJobWorker, AsyncJobWorkerModeError
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
