from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from trms_backend.api.invoice_validation_refresh import refresh_validations_for_material
from trms_backend.application.async_jobs import AsyncJobProcessor
from trms_backend.application.metrics import MetricsCollector, NoOpMetricsCollector
from trms_backend.application.recognition_preparation import (
    RecognitionMaterialNotFoundError,
    RecognitionPreparationService,
    RecognitionTaskExecutionConflictError,
    RecognitionTaskExecutionNotFoundError,
)
from trms_backend.application.recognition_invoice_auto_create import (
    RecognitionInvoiceAutoCreateService,
)
from trms_backend.application.supporting_material_auto_link import (
    SupportingMaterialAutoLinkService,
)
from trms_backend.domain.invoices import InvoiceRepository, ValidationRepository
from trms_backend.domain.materials import MaterialRepository
from trms_backend.domain.recognitions import RecognitionTaskRecord, RecognitionTaskRepository
from trms_backend.domain.confirmations import ConfirmationRepository
from trms_backend.domain.splits import ExpenseSplitRepository
from trms_backend.domain.tasks import TaskRepository
from trms_backend.logging_safety import sanitize_log_fields

LOGGER = logging.getLogger("trms_backend.worker")


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
        split_repository: ExpenseSplitRepository,
        confirmation_repository: ConfirmationRepository,
        recognition_preparation_service: RecognitionPreparationService,
        batch_size: int = 10,
        max_workers: int = 1,
        metrics_collector: MetricsCollector | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._material_repository = material_repository
        self._invoice_repository = invoice_repository
        self._validation_repository = validation_repository
        self._recognition_task_repository = recognition_task_repository
        self._recognition_preparation_service = recognition_preparation_service
        self._batch_size = batch_size
        self._max_workers = max(1, max_workers)
        self._metrics_collector = metrics_collector or NoOpMetricsCollector()
        self._recognition_invoice_auto_create_service = RecognitionInvoiceAutoCreateService(
            task_repository=task_repository,
            material_repository=material_repository,
            invoice_repository=invoice_repository,
            split_repository=split_repository,
            confirmation_repository=confirmation_repository,
            supporting_material_auto_link_service=SupportingMaterialAutoLinkService(
                material_repository=material_repository,
                invoice_repository=invoice_repository,
            ),
        )

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def run_once(self) -> int:
        pending_tasks = self._recognition_task_repository.list_pending(limit=self._batch_size)
        if not pending_tasks:
            return 0
        if self._max_workers == 1 or len(pending_tasks) == 1:
            return sum(self._process_task(task) for task in pending_tasks)

        processed_count = 0
        with ThreadPoolExecutor(
            max_workers=min(self._max_workers, len(pending_tasks)),
            thread_name_prefix="trms-recognition-worker",
        ) as executor:
            futures = [executor.submit(self._process_task, task) for task in pending_tasks]
            for future in as_completed(futures):
                processed_count += future.result()
        return processed_count

    def _process_task(self, task: RecognitionTaskRecord) -> int:
        try:
            updated = self._recognition_preparation_service.execute(task.id)
        except (
            RecognitionTaskExecutionConflictError,
            RecognitionTaskExecutionNotFoundError,
            RecognitionMaterialNotFoundError,
        ) as error:
            LOGGER.warning(
                "recognition_worker_job_skipped %s",
                sanitize_log_fields(
                    {
                        "recognition_task_id": task.id,
                        "material_id": task.material_id,
                        "reason": str(error),
                    }
                ),
            )
            return 0

        self._recognition_invoice_auto_create_service.try_upsert_invoice_from_recognition(updated)
        refresh_validations_for_material(
            updated.material_id,
            task_repository=self._task_repository,
            material_repository=self._material_repository,
            invoice_repository=self._invoice_repository,
            validation_repository=self._validation_repository,
            recognition_task_repository=self._recognition_task_repository,
            metrics_collector=self._metrics_collector,
        )
        LOGGER.info(
            "recognition_worker_job_processed %s",
            sanitize_log_fields(
                {
                    "recognition_task_id": updated.id,
                    "material_id": updated.material_id,
                    "status": updated.status,
                    "failure_reason": updated.failure.reason if updated.failure is not None else None,
                }
            ),
        )
        return 1


class NoOpAsyncJobProcessor(AsyncJobProcessor):
    def __init__(self, job_type: str) -> None:
        self.job_type = job_type

    def run_once(self) -> int:
        return 0
