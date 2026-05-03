from datetime import UTC, date, datetime, timedelta

from trms_backend.application.metrics import InMemoryMetricsCollector
from trms_backend.application.material_submission import (
    MaterialSubmissionService,
    SubmittedMaterialFile,
)
from trms_backend.domain.audit_logs import InMemoryAuditLogRepository
from trms_backend.domain.materials import (
    InMemoryMaterialRepository,
    MaterialStatus,
    MaterialType,
    SubmissionChannel,
)
from trms_backend.domain.recognitions import RecognitionTaskCreate
from trms_backend.domain.tasks import InMemoryTaskRepository, TaskCreate, TaskStatus
from trms_backend.infrastructure.storage import LocalMaterialFileStorage


class RecordingRecognitionTaskRepository:
    def __init__(self) -> None:
        self.created_material_ids: list[str] = []

    def create(self, data: RecognitionTaskCreate):
        self.created_material_ids.append(data.material_id)
        return None


def create_open_task(task_repository: InMemoryTaskRepository) -> str:
    task = task_repository.create(
        TaskCreate(
            competition_name="CCPC Final",
            competition_location="Shanghai",
            competition_start_date=date(2026, 5, 1),
            competition_end_date=date(2026, 5, 3),
            deadline=datetime.now(UTC) + timedelta(days=3),
            email_submission_key="ccpc-final-material-service",
            member_ids=["2250001", "2250002"],
            fee_categories=["registration", "railway"],
            administrator_id="admin-1",
            administrator_ids=["admin-1"],
            project_info="ACM Project",
            reimburser_info="Lab Manager",
            invoice_title="同济大学",
            tax_number="91310000123456789X",
        )
    )
    task_repository.update_status(task.id, TaskStatus.OPEN)
    return task.id


def test_material_submission_service_reuses_same_assigned_flow_for_all_channels(tmp_path):
    task_repository = InMemoryTaskRepository()
    task_id = create_open_task(task_repository)
    material_repository = InMemoryMaterialRepository()
    recognition_task_repository = RecordingRecognitionTaskRepository()
    audit_log_repository = InMemoryAuditLogRepository()
    metrics_collector = InMemoryMetricsCollector()
    service = MaterialSubmissionService(
        task_repository,
        material_repository,
        LocalMaterialFileStorage(tmp_path / "material-storage"),
        recognition_task_repository,
        audit_log_repository,
        metrics_collector,
    )

    for channel in (
        SubmissionChannel.WEB,
        SubmissionChannel.CLI,
        SubmissionChannel.TELEGRAM,
        SubmissionChannel.EMAIL,
    ):
        result = service.submit_to_task(
            task_id=task_id,
            submitter_id="2250001",
            actor_id="2250001",
            channel=channel,
            material_type=MaterialType.INVOICE,
            files=[
                SubmittedMaterialFile(
                    original_filename=f"{channel.value}.pdf",
                    content_type="application/pdf",
                    content=channel.value.encode("utf-8"),
                )
            ],
        )

        assert result.failures == []
        assert len(result.records) == 1
        assert result.records[0].status is MaterialStatus.ASSIGNED
        assert result.records[0].task_id == task_id
        assert result.records[0].submitter_id == "2250001"
        assert result.records[0].channel is channel

    assert len(recognition_task_repository.created_material_ids) == 4
    snapshot = metrics_collector.snapshot()
    assert snapshot["uploads"]["succeeded"] == 4
    assert snapshot["uploads"]["failed"] == 0
    assert snapshot["uploads"]["success_by_channel"] == {
        "web": 1,
        "cli": 1,
        "telegram": 1,
        "email": 1,
    }
    assert snapshot["recognition_tasks"]["by_status"] == {"pending": 4}


def test_material_submission_service_creates_pending_assignment_without_channel_specific_rules(
    tmp_path,
):
    task_repository = InMemoryTaskRepository()
    material_repository = InMemoryMaterialRepository()
    recognition_task_repository = RecordingRecognitionTaskRepository()
    audit_log_repository = InMemoryAuditLogRepository()
    metrics_collector = InMemoryMetricsCollector()
    service = MaterialSubmissionService(
        task_repository,
        material_repository,
        LocalMaterialFileStorage(tmp_path / "material-storage"),
        recognition_task_repository,
        audit_log_repository,
        metrics_collector,
    )

    result = service.submit_pending_assignment(
        actor_id="email:member@example.com",
        channel=SubmissionChannel.EMAIL,
        material_type=MaterialType.PAYMENT_RECORD,
        files=[
            SubmittedMaterialFile(
                original_filename="payment.pdf",
                content_type="application/pdf",
                content=b"payment-record",
            )
        ],
        task_id_hint="task-hint-001",
        submitter_id_hint="2250999",
    )

    assert result.failures == []
    assert len(result.records) == 1
    material = result.records[0]
    assert material.status is MaterialStatus.PENDING_ASSIGNMENT
    assert material.task_id is None
    assert material.submitter_id is None
    assert material.task_id_hint == "task-hint-001"
    assert material.submitter_id_hint == "2250999"
    assert material.channel is SubmissionChannel.EMAIL
    assert material.material_type is MaterialType.PAYMENT_RECORD
    assert recognition_task_repository.created_material_ids == [material.id]
    snapshot = metrics_collector.snapshot()
    assert snapshot["uploads"]["succeeded"] == 1
    assert snapshot["recognition_tasks"]["by_status"] == {"pending": 1}


def test_material_submission_service_records_upload_failures_in_metrics(tmp_path):
    task_repository = InMemoryTaskRepository()
    task_id = create_open_task(task_repository)
    material_repository = InMemoryMaterialRepository()
    recognition_task_repository = RecordingRecognitionTaskRepository()
    audit_log_repository = InMemoryAuditLogRepository()
    metrics_collector = InMemoryMetricsCollector()
    service = MaterialSubmissionService(
        task_repository,
        material_repository,
        LocalMaterialFileStorage(tmp_path / "material-storage"),
        recognition_task_repository,
        audit_log_repository,
        metrics_collector,
    )

    result = service.submit_to_task(
        task_id=task_id,
        submitter_id="2250001",
        actor_id="2250001",
        channel=SubmissionChannel.WEB,
        material_type=MaterialType.INVOICE,
        files=[
            SubmittedMaterialFile(
                original_filename="ok.pdf",
                content_type="application/pdf",
                content=b"valid",
            ),
            SubmittedMaterialFile(
                original_filename="empty.pdf",
                content_type="application/pdf",
                content=b"",
            ),
        ],
    )

    assert len(result.records) == 1
    assert len(result.failures) == 1
    snapshot = metrics_collector.snapshot()
    assert snapshot["uploads"]["total"] == 2
    assert snapshot["uploads"]["succeeded"] == 1
    assert snapshot["uploads"]["failed"] == 1
    assert snapshot["uploads"]["failure_by_code"] == {"empty_file": 1}
    assert snapshot["recognition_tasks"]["by_status"] == {"pending": 1}
