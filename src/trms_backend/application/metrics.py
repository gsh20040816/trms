from __future__ import annotations

from collections import Counter, defaultdict
from threading import Lock
from typing import Protocol

from trms_backend.domain.exports import ExportArtifactFormat, ExportArtifactKind, TaskExportJobStatus
from trms_backend.domain.invoices import ValidationResult, ValidationStatus
from trms_backend.domain.materials import MaterialType, SubmissionChannel
from trms_backend.domain.recognitions import RecognitionFailureStage, RecognitionTaskStatus


class MetricsCollector(Protocol):
    def record_material_upload_result(
        self,
        *,
        channel: SubmissionChannel,
        material_type: MaterialType,
        succeeded: bool,
        failure_code: str | None = None,
    ) -> None:
        raise NotImplementedError

    def record_recognition_task_status(
        self,
        *,
        status: RecognitionTaskStatus,
        failure_stage: RecognitionFailureStage | None = None,
    ) -> None:
        raise NotImplementedError

    def record_validation_results(self, *, results: list[ValidationResult]) -> None:
        raise NotImplementedError

    def record_export_job_status(
        self,
        *,
        kind: ExportArtifactKind,
        format: ExportArtifactFormat,
        status: TaskExportJobStatus,
    ) -> None:
        raise NotImplementedError


class NoOpMetricsCollector(MetricsCollector):
    def record_material_upload_result(
        self,
        *,
        channel: SubmissionChannel,
        material_type: MaterialType,
        succeeded: bool,
        failure_code: str | None = None,
    ) -> None:
        return None

    def record_recognition_task_status(
        self,
        *,
        status: RecognitionTaskStatus,
        failure_stage: RecognitionFailureStage | None = None,
    ) -> None:
        return None

    def record_validation_results(self, *, results: list[ValidationResult]) -> None:
        return None

    def record_export_job_status(
        self,
        *,
        kind: ExportArtifactKind,
        format: ExportArtifactFormat,
        status: TaskExportJobStatus,
    ) -> None:
        return None


class InMemoryMetricsCollector(MetricsCollector):
    def __init__(self) -> None:
        self._lock = Lock()
        self._upload_total = 0
        self._upload_success_total = 0
        self._upload_failure_total = 0
        self._upload_success_by_channel: Counter[str] = Counter()
        self._upload_failure_by_code: Counter[str] = Counter()
        self._upload_by_material_type: Counter[str] = Counter()
        self._recognition_status_counts: Counter[str] = Counter()
        self._recognition_failure_stage_counts: Counter[str] = Counter()
        self._validation_failed_rule_counts: Counter[str] = Counter()
        self._validation_pending_rule_counts: Counter[str] = Counter()
        self._export_status_counts: Counter[str] = Counter()
        self._export_status_by_kind: dict[str, Counter[str]] = defaultdict(Counter)
        self._export_status_by_format: dict[str, Counter[str]] = defaultdict(Counter)

    def record_material_upload_result(
        self,
        *,
        channel: SubmissionChannel,
        material_type: MaterialType,
        succeeded: bool,
        failure_code: str | None = None,
    ) -> None:
        with self._lock:
            self._upload_total += 1
            self._upload_by_material_type[material_type.value] += 1
            if succeeded:
                self._upload_success_total += 1
                self._upload_success_by_channel[channel.value] += 1
                return
            self._upload_failure_total += 1
            self._upload_failure_by_code[failure_code or "unknown"] += 1

    def record_recognition_task_status(
        self,
        *,
        status: RecognitionTaskStatus,
        failure_stage: RecognitionFailureStage | None = None,
    ) -> None:
        with self._lock:
            self._recognition_status_counts[status.value] += 1
            if failure_stage is not None:
                self._recognition_failure_stage_counts[failure_stage.value] += 1

    def record_validation_results(self, *, results: list[ValidationResult]) -> None:
        with self._lock:
            for result in results:
                if result.status is ValidationStatus.FAILED:
                    self._validation_failed_rule_counts[result.rule_code] += 1
                elif result.status is ValidationStatus.PENDING:
                    self._validation_pending_rule_counts[result.rule_code] += 1

    def record_export_job_status(
        self,
        *,
        kind: ExportArtifactKind,
        format: ExportArtifactFormat,
        status: TaskExportJobStatus,
    ) -> None:
        with self._lock:
            self._export_status_counts[status.value] += 1
            self._export_status_by_kind[kind.value][status.value] += 1
            self._export_status_by_format[format.value][status.value] += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            upload_total = self._upload_total
            upload_success_total = self._upload_success_total
            upload_failure_total = self._upload_failure_total
            return {
                "uploads": {
                    "total": upload_total,
                    "succeeded": upload_success_total,
                    "failed": upload_failure_total,
                    "success_rate": (
                        upload_success_total / upload_total if upload_total else 0.0
                    ),
                    "failure_rate": (
                        upload_failure_total / upload_total if upload_total else 0.0
                    ),
                    "success_by_channel": dict(self._upload_success_by_channel),
                    "by_material_type": dict(self._upload_by_material_type),
                    "failure_by_code": dict(self._upload_failure_by_code),
                },
                "recognition_tasks": {
                    "by_status": dict(self._recognition_status_counts),
                    "failure_by_stage": dict(self._recognition_failure_stage_counts),
                },
                "validation_results": {
                    "failed_rule_counts": dict(self._validation_failed_rule_counts),
                    "pending_rule_counts": dict(self._validation_pending_rule_counts),
                },
                "export_jobs": {
                    "by_status": dict(self._export_status_counts),
                    "by_kind": {
                        kind: dict(counts)
                        for kind, counts in self._export_status_by_kind.items()
                    },
                    "by_format": {
                        format_name: dict(counts)
                        for format_name, counts in self._export_status_by_format.items()
                    },
                },
            }
