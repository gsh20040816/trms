from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from trms_backend.application.material_submission import (
    MaterialSubmissionBatchResult,
    MaterialSubmissionService,
    SubmittedMaterialFile,
)
from trms_backend.application.metrics import MetricsCollector, NoOpMetricsCollector
from trms_backend.application.recognition_audit import record_recognition_result_audit
from trms_backend.application.recognition_invoice_auto_create import (
    RecognitionInvoiceAutoCreateService,
)
from trms_backend.application.recognition_preparation import (
    RecognitionMaterialNotFoundError,
    RecognitionPreparationService,
    RecognitionTaskExecutionConflictError,
    RecognitionTaskExecutionNotFoundError,
)
from trms_backend.application.supporting_material_auto_link import SupportingMaterialAutoLinkService
from trms_backend.domain.audit_logs import AuditLogRepository
from trms_backend.domain.confirmations import ConfirmationRepository
from trms_backend.domain.invoices import InvoiceRepository, ValidationRepository
from trms_backend.domain.materials import MaterialRecord, MaterialRepository, MaterialType, SubmissionChannel
from trms_backend.domain.recognitions import (
    RecognitionFailureDetail,
    RecognitionFailureStage,
    RecognitionResultPayload,
    RecognitionTaskRepository,
    RecognitionTaskStatus,
)
from trms_backend.domain.splits import ExpenseSplitRepository
from trms_backend.domain.tasks import (
    TaskRepository,
    TaskSubmissionDeadlinePassedError,
    TaskSubmitterNotMemberError,
)
from trms_backend.runtime_config import AsyncJobMode
from trms_backend.api.invoice_validation_refresh import (
    refresh_invoice_validations,
    refresh_validations_for_material,
)


@dataclass(frozen=True)
class TaskMaterialUploadItem:
    material: MaterialRecord
    recognition_status: str


@dataclass(frozen=True)
class TaskMaterialUploadResult:
    batch_result: MaterialSubmissionBatchResult
    items: list[TaskMaterialUploadItem]
    recognition_dispatch: dict[str, str]


class TaskMaterialUploadService:
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
        material_submission_service: MaterialSubmissionService,
        recognition_preparation_service: RecognitionPreparationService,
        audit_log_repository: AuditLogRepository,
        async_job_mode: AsyncJobMode,
        metrics_collector: MetricsCollector | None = None,
        recognition_provider_configured_resolver: Callable[[], bool] | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._material_repository = material_repository
        self._invoice_repository = invoice_repository
        self._validation_repository = validation_repository
        self._recognition_task_repository = recognition_task_repository
        self._material_submission_service = material_submission_service
        self._recognition_preparation_service = recognition_preparation_service
        self._audit_log_repository = audit_log_repository
        self._async_job_mode = async_job_mode
        self._metrics = metrics_collector or NoOpMetricsCollector()
        self._recognition_provider_configured_resolver = recognition_provider_configured_resolver
        self._supporting_material_auto_link_service = SupportingMaterialAutoLinkService(
            material_repository=material_repository,
            invoice_repository=invoice_repository,
            recognition_task_repository=recognition_task_repository,
        )
        self._recognition_invoice_auto_create_service = RecognitionInvoiceAutoCreateService(
            task_repository=task_repository,
            material_repository=material_repository,
            invoice_repository=invoice_repository,
            split_repository=split_repository,
            confirmation_repository=confirmation_repository,
            supporting_material_auto_link_service=self._supporting_material_auto_link_service,
        )

    def submit_to_task(
        self,
        *,
        task_id: str,
        submitter_id: str,
        actor_id: str,
        channel: SubmissionChannel,
        material_type: MaterialType,
        files: list[SubmittedMaterialFile],
        request_id: str,
    ) -> TaskMaterialUploadResult:
        batch_result = self._material_submission_service.submit_to_task(
            task_id=task_id,
            submitter_id=submitter_id,
            actor_id=actor_id,
            channel=channel,
            material_type=material_type,
            files=files,
            request_id=request_id,
        )

        auto_linked_invoice_ids: set[str] = set()
        for record in batch_result.records:
            for link in self._supporting_material_auto_link_service.auto_link_for_material(record):
                auto_linked_invoice_ids.add(link.invoice_id)
        for invoice_id in auto_linked_invoice_ids:
            refresh_invoice_validations(
                invoice_id,
                task_repository=self._task_repository,
                material_repository=self._material_repository,
                invoice_repository=self._invoice_repository,
                validation_repository=self._validation_repository,
                recognition_task_repository=self._recognition_task_repository,
                metrics_collector=self._metrics,
            )

        recognition_status_by_material_id, recognition_dispatch = (
            self._dispatch_recognition_tasks_for_uploaded_materials(
                material_ids=[record.id for record in batch_result.records],
                actor_id=actor_id,
                request_id=request_id,
            )
        )
        items = [
            TaskMaterialUploadItem(
                material=self._material_repository.get(record.id) or record,
                recognition_status=recognition_status_by_material_id.get(record.id, "pending"),
            )
            for record in batch_result.records
        ]
        return TaskMaterialUploadResult(
            batch_result=batch_result,
            items=items,
            recognition_dispatch=recognition_dispatch,
        )

    def _dispatch_recognition_tasks_for_uploaded_materials(
        self,
        *,
        material_ids: list[str],
        actor_id: str,
        request_id: str,
    ) -> tuple[dict[str, str], dict[str, str]]:
        recognition_status_by_material_id = {
            material_id: "pending"
            for material_id in material_ids
        }
        if self._async_job_mode == "worker":
            return recognition_status_by_material_id, {
                "mode": "worker",
                "status": "queued",
                "message": "识别已入队等待 worker 消费；在 worker 未运行前，材料会保持“识别排队中”。",
            }

        if (
            self._recognition_provider_configured_resolver is not None
            and not self._recognition_provider_configured_resolver()
        ):
            failure = RecognitionFailureDetail(
                stage=RecognitionFailureStage.AI,
                reason="llm_provider_not_configured",
            )
            for material_id in material_ids:
                recognition_tasks = self._recognition_task_repository.list_by_material(material_id)
                material = self._material_repository.get(material_id)
                if not recognition_tasks or material is None:
                    continue
                latest_task = recognition_tasks[-1]
                updated = self._recognition_task_repository.update_status(
                    latest_task.id,
                    RecognitionTaskStatus.FAILED,
                    result=RecognitionResultPayload(
                        raw_response={
                            "preparation": {
                                "material_id": material.id,
                                "original_filename": material.original_filename,
                                "content_type": material.content_type,
                            }
                        }
                    ),
                    failure=failure,
                    expected_current_status=RecognitionTaskStatus.PENDING,
                )
                if updated is None:
                    continue
                record_recognition_result_audit(
                    self._audit_log_repository,
                    actor_id=actor_id,
                    recognition_task=updated,
                    task_id=material.task_id,
                    request_id=request_id,
                )
                self._metrics.record_recognition_task_status(
                    status=updated.status,
                    failure_stage=failure.stage,
                )
                recognition_status_by_material_id[material_id] = updated.status.value
            return recognition_status_by_material_id, {
                "mode": "in_process",
                "status": "executed",
                "message": "当前环境未配置识别服务；材料已接收，但无法自动识别，请配置 provider 或手动补录。",
            }

        for material_id in material_ids:
            recognition_tasks = self._recognition_task_repository.list_by_material(material_id)
            if not recognition_tasks:
                continue
            latest_task = recognition_tasks[-1]
            try:
                updated = self._recognition_preparation_service.execute(
                    latest_task.id,
                    actor_id=actor_id,
                    request_id=request_id,
                )
            except (
                RecognitionTaskExecutionNotFoundError,
                RecognitionTaskExecutionConflictError,
                RecognitionMaterialNotFoundError,
            ):
                continue
            self._recognition_invoice_auto_create_service.try_upsert_invoice_from_recognition(
                updated
            )
            material = self._material_repository.get(updated.material_id)
            if material is not None:
                self._supporting_material_auto_link_service.auto_link_for_material(
                    material,
                    recognition_task=updated,
                )
            refresh_validations_for_material(
                updated.material_id,
                task_repository=self._task_repository,
                material_repository=self._material_repository,
                invoice_repository=self._invoice_repository,
                validation_repository=self._validation_repository,
                recognition_task_repository=self._recognition_task_repository,
                metrics_collector=self._metrics,
            )
            recognition_status_by_material_id[material_id] = updated.status.value

        return recognition_status_by_material_id, {
            "mode": "in_process",
            "status": "executed",
            "message": "识别已在当前请求内执行；如结果仍待确认，请继续补录或复核关键字段。",
        }
