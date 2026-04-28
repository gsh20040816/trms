from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import sleep as default_sleep

from trms_backend.runtime_config import AsyncJobConfig, AsyncJobMode


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
    def registered_job_types(self) -> tuple[str, ...]:
        return tuple(processor.job_type for processor in self._processors)

    def run_once(self) -> AsyncJobWorkerIterationResult:
        self._ensure_worker_mode()

        processed_counts: dict[str, int] = {}
        for processor in self._processors:
            processed_counts[processor.job_type] = processor.run_once()
        return AsyncJobWorkerIterationResult(processed_counts=processed_counts)

    def run_forever(self) -> None:
        self._ensure_worker_mode()

        while True:
            result = self.run_once()
            if result.total_processed == 0:
                self._sleep(self._config.worker_poll_interval_seconds)

    def _ensure_worker_mode(self) -> None:
        if self._config.mode != "worker":
            raise AsyncJobWorkerModeError(self._config.mode)
