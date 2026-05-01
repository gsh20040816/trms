from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
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
                    "registered_job_types": list(self.registered_job_types),
                }
            ),
        )
        processed_counts: dict[str, int] = {}
        for processor in self._processors:
            processed_counts[processor.job_type] = processor.run_once()
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
                            "registered_job_types": list(self.registered_job_types),
                        }
                    ),
                )
                self._sleep(self._config.worker_poll_interval_seconds)

    def _ensure_worker_mode(self) -> None:
        if self._config.mode != "worker":
            raise AsyncJobWorkerModeError(self._config.mode)
