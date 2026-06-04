from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from concurrent.futures import Future, wait
from dataclasses import dataclass
from threading import Thread
from time import monotonic
from time import sleep as default_sleep

from trms_backend.logging_safety import sanitize_log_fields
from trms_backend.runtime_config import AsyncJobConfig, AsyncJobMode

LOGGER = logging.getLogger("trms_backend.worker")


class AsyncJobWorkerModeError(RuntimeError):
    def __init__(self, mode: AsyncJobMode) -> None:
        self.mode = mode
        super().__init__(
            "async job worker requires TRMS_ASYNC_JOB_MODE=worker; "
            f"current mode is {mode}"
        )


class AsyncJobProcessor:
    job_type = "unknown"

    def run_once(self) -> int:  # pragma: no cover - protocol-like default
        raise NotImplementedError


@dataclass
class _RunningProcessorTask:
    processor: AsyncJobProcessor
    future: Future[int]
    started_at_monotonic: float
    timed_out: bool = False


@dataclass(frozen=True)
class AsyncJobWorkerIterationResult:
    processed_counts: dict[str, int]

    @property
    def total_processed(self) -> int:
        return sum(self.processed_counts.values())


class AsyncJobWorker:
    def __init__(
        self,
        config: AsyncJobConfig,
        *,
        processors: Sequence[AsyncJobProcessor] = (),
        sleep: Callable[[float], None] = default_sleep,
    ) -> None:
        self._config = config
        self._processors = tuple(processors)
        self._sleep = sleep
        self._running_processor_tasks: dict[str, _RunningProcessorTask] = {}

    @property
    def mode(self) -> AsyncJobMode:
        return self._config.mode

    @property
    def poll_interval_seconds(self) -> float:
        return self._config.worker_poll_interval_seconds

    @property
    def worker_concurrency(self) -> int:
        return self._config.worker_concurrency

    @property
    def worker_task_timeout_seconds(self) -> float:
        return self._config.worker_task_timeout_seconds

    @property
    def registered_job_types(self) -> tuple[str, ...]:
        return tuple(processor.job_type for processor in self._processors)

    def run_once(self) -> AsyncJobWorkerIterationResult:
        self._ensure_worker_mode()

        LOGGER.info(
            "worker_poll_start %s",
            sanitize_log_fields(
                {
                    "mode": self.mode,
                    "poll_interval_seconds": self.poll_interval_seconds,
                    "worker_concurrency": self.worker_concurrency,
                    "worker_task_timeout_seconds": self.worker_task_timeout_seconds,
                    "registered_job_types": list(self.registered_job_types),
                }
            ),
        )
        processed_counts: dict[str, int] = {
            processor.job_type: 0 for processor in self._processors
        }
        pending_tasks: dict[Future[int], _RunningProcessorTask] = {}
        for processor in self._processors:
            existing_task = self._running_processor_tasks.get(processor.job_type)
            if existing_task is not None:
                if existing_task.future.done():
                    self._finish_processor_task(
                        processor.job_type,
                        existing_task,
                        completed_after_timeout=True,
                    )
                else:
                    self._log_processor_still_running(processor.job_type, existing_task)
                    continue

            task = self._start_processor_task(processor)
            self._running_processor_tasks[processor.job_type] = task
            pending_tasks[task.future] = task

        if pending_tasks:
            completed_futures, timed_out_futures = wait(
                pending_tasks.keys(),
                timeout=self.worker_task_timeout_seconds,
            )
            for future in completed_futures:
                task = pending_tasks[future]
                processed_counts[task.processor.job_type] = self._finish_processor_task(
                    task.processor.job_type,
                    task,
                    completed_after_timeout=False,
                )
            for future in timed_out_futures:
                task = pending_tasks[future]
                if future.done():
                    processed_counts[task.processor.job_type] = self._finish_processor_task(
                        task.processor.job_type,
                        task,
                        completed_after_timeout=False,
                    )
                    continue
                task.timed_out = True
                self._log_processor_timeout(task.processor.job_type, task)

        result = AsyncJobWorkerIterationResult(processed_counts=processed_counts)
        LOGGER.info(
            "worker_poll_complete %s",
            sanitize_log_fields(
                {
                    "processed_counts": processed_counts,
                    "total_processed": result.total_processed,
                }
            ),
        )
        return result

    def run_forever(self) -> None:
        self._ensure_worker_mode()

        while True:
            result = self.run_once()
            if result.total_processed == 0:
                LOGGER.info(
                    "worker_idle_wait %s",
                    sanitize_log_fields(
                        {
                            "sleep_seconds": self._config.worker_poll_interval_seconds,
                            "worker_concurrency": self.worker_concurrency,
                            "worker_task_timeout_seconds": self.worker_task_timeout_seconds,
                            "registered_job_types": list(self.registered_job_types),
                        }
                    ),
                )
                self._sleep(self._config.worker_poll_interval_seconds)

    def _start_processor_task(self, processor: AsyncJobProcessor) -> _RunningProcessorTask:
        future: Future[int] = Future()
        task = _RunningProcessorTask(
            processor=processor,
            future=future,
            started_at_monotonic=monotonic(),
        )
        thread = Thread(
            target=self._run_processor_task,
            args=(processor, future),
            name=f"trms-worker-{processor.job_type}",
            daemon=True,
        )
        thread.start()
        return task

    def _run_processor_task(
        self,
        processor: AsyncJobProcessor,
        future: Future[int],
    ) -> None:
        if not future.set_running_or_notify_cancel():
            return
        try:
            processed_count = processor.run_once()
        except Exception as error:
            future.set_exception(error)
            return
        future.set_result(processed_count)

    def _finish_processor_task(
        self,
        job_type: str,
        task: _RunningProcessorTask,
        *,
        completed_after_timeout: bool,
    ) -> int:
        current_task = self._running_processor_tasks.get(job_type)
        if current_task is task:
            del self._running_processor_tasks[job_type]
        try:
            processed_count = task.future.result()
        except Exception as error:
            LOGGER.exception(
                "worker_processor_failed %s",
                sanitize_log_fields(
                    {
                        "job_type": job_type,
                        "error": str(error),
                    }
                ),
            )
            return 0

        if completed_after_timeout or task.timed_out:
            LOGGER.info(
                "worker_processor_late_complete %s",
                sanitize_log_fields(
                    {
                        "job_type": job_type,
                        "processed_count": processed_count,
                        "elapsed_seconds": monotonic() - task.started_at_monotonic,
                        "timeout_seconds": self.worker_task_timeout_seconds,
                    }
                ),
            )
        return processed_count

    def _log_processor_timeout(
        self,
        job_type: str,
        task: _RunningProcessorTask,
    ) -> None:
        LOGGER.error(
            "worker_processor_timeout %s",
            sanitize_log_fields(
                {
                    "job_type": job_type,
                    "elapsed_seconds": monotonic() - task.started_at_monotonic,
                    "timeout_seconds": self.worker_task_timeout_seconds,
                }
            ),
        )

    def _log_processor_still_running(
        self,
        job_type: str,
        task: _RunningProcessorTask,
    ) -> None:
        LOGGER.warning(
            "worker_processor_still_running %s",
            sanitize_log_fields(
                {
                    "job_type": job_type,
                    "elapsed_seconds": monotonic() - task.started_at_monotonic,
                    "timeout_seconds": self.worker_task_timeout_seconds,
                }
            ),
        )

    def _ensure_worker_mode(self) -> None:
        if self._config.mode != "worker":
            raise AsyncJobWorkerModeError(self._config.mode)
