from __future__ import annotations

from trms_backend.api.invoice_validation_refresh import refresh_validations_for_material
from trms_backend.application.async_jobs import AsyncJobProcessor
from trms_backend.application.metrics import MetricsCollector, NoOpMetricsCollector
from trms_backend.application.recognition_preparation import (
    RecognitionMaterialNotFoundError,
    RecognitionPreparationService,
    RecognitionTaskExecutionConflictError,
    RecognitionTaskExecutionNotFoundError,
)
from trms_backend.domain.invoices import InvoiceRepository, ValidationRepository
from trms_backend.domain.materials import MaterialRepository
from trms_backend.domain.recognitions import RecognitionTaskRepository
from trms_backend.domain.tasks import TaskRepository


class RecognitionAsyncJobProcessor(AsyncJobProcessor):
    job_type = "recognition"

    def __init__(
        self,
        *,
        task_repository: TaskRepository,
        material_repository: MaterialRepository,
        invoice_repository: InvoiceRepository,
        validation_repository: ValidationRepository,
        recognition_task_repository: RecognitionTaskRepository,
        recognition_preparation_service: RecognitionPreparationService,
        batch_size: int = 10,
        metrics_collector: MetricsCollector | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._material_repository = material_repository
        self._invoice_repository = invoice_repository
        self._validation_repository = validation_repository
        self._recognition_task_repository = recognition_task_repository
        self._recognition_preparation_service = recognition_preparation_service
        self._batch_size = batch_size
        self._metrics_collector = metrics_collector or NoOpMetricsCollector()

    def run_once(self) -> int:
        processed_count = 0
        for task in self._recognition_task_repository.list_pending(limit=self._batch_size):
            try:
                updated = self._recognition_preparation_service.execute(task.id)
            except (
                RecognitionTaskExecutionConflictError,
                RecognitionTaskExecutionNotFoundError,
                RecognitionMaterialNotFoundError,
            ):
                continue

            refresh_validations_for_material(
                updated.material_id,
                task_repository=self._task_repository,
                material_repository=self._material_repository,
                invoice_repository=self._invoice_repository,
                validation_repository=self._validation_repository,
                recognition_task_repository=self._recognition_task_repository,
                metrics_collector=self._metrics_collector,
            )
            processed_count += 1
        return processed_count


class NoOpAsyncJobProcessor(AsyncJobProcessor):
    def __init__(self, job_type: str) -> None:
        self.job_type = job_type

    def run_once(self) -> int:
        return 0
