from datetime import UTC, datetime

from trms_backend.application.material_submission import (
    MaterialSubmissionBatchResult,
    MaterialSubmissionTaskNotOpenError,
)
from trms_backend.application.task_material_upload import (
    TaskMaterialUploadItem,
    TaskMaterialUploadResult,
)
from trms_backend.application.telegram_binding_oauth import TelegramBindingOauthService
from trms_backend.application.telegram_bot import (
    TelegramBotWorkflowService,
    TelegramIncomingFile,
)
from trms_backend.domain.global_invoice_config import GlobalInvoiceConfig
from trms_backend.domain.materials import (
    MaterialRecord,
    MaterialStatus,
    MaterialType,
    SubmissionChannel,
)
from trms_backend.domain.tasks import InMemoryTaskRepository, TaskCreateInput, TaskStatus, resolve_task_create
from trms_backend.domain.telegram_bindings import InMemoryTelegramAccountBindingRepository
from trms_backend.domain.telegram_bot import (
    InMemoryTelegramBindingAuthorizationRepository,
    InMemoryTelegramTaskContextRepository,
)


class FakeTaskMaterialUploadService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.mode = "success"

    def submit_to_task(self, **kwargs):
        self.calls.append(kwargs)
        if self.mode == "task_not_open":
            raise MaterialSubmissionTaskNotOpenError(kwargs["task_id"])
        if self.mode != "success":
            raise AssertionError(f"unexpected fake mode: {self.mode}")
        material = MaterialRecord(
            id="MAT-001",
            status=MaterialStatus.ASSIGNED,
            task_id=str(kwargs["task_id"]),
            submitter_id=str(kwargs["submitter_id"]),
            task_id_hint=None,
            submitter_id_hint=None,
            channel=SubmissionChannel.TELEGRAM,
            material_type=MaterialType.INVOICE,
            storage_key="TASK-001/invoice.pdf",
            original_filename="invoice.pdf",
            content_type="application/pdf",
            size_bytes=128,
            sha256="a" * 64,
            duplicate_of=None,
            claimed_by=None,
            claimed_at=None,
            created_at=datetime.now(UTC),
        )
        return TaskMaterialUploadResult(
            batch_result=MaterialSubmissionBatchResult(records=[material], failures=[]),
            items=[
                TaskMaterialUploadItem(
                    material=material,
                    recognition_status="pending",
                )
            ],
            recognition_dispatch={"status": "queued", "mode": "worker"},
        )


def build_workflow_service():
    task_repository = InMemoryTaskRepository()
    binding_repository = InMemoryTelegramAccountBindingRepository()
    authorization_repository = InMemoryTelegramBindingAuthorizationRepository()
    task_context_repository = InMemoryTelegramTaskContextRepository()
    upload_service = FakeTaskMaterialUploadService()
    oauth_service = TelegramBindingOauthService(
        authorization_repository,
        binding_repository,
    )
    workflow_service = TelegramBotWorkflowService(
        public_web_base_url="https://trms.example.edu",
        binding_oauth_service=oauth_service,
        binding_repository=binding_repository,
        task_repository=task_repository,
        task_context_repository=task_context_repository,
        task_material_upload_service=upload_service,
    )
    return (
        workflow_service,
        task_repository,
        binding_repository,
        oauth_service,
        task_context_repository,
        upload_service,
    )


def create_task(task_repository: InMemoryTaskRepository, *, submission_key: str, status: TaskStatus) -> str:
    payload = TaskCreateInput.model_validate(
        {
            "competition_name": f"Task {submission_key}",
            "competition_location": "Shanghai",
            "competition_start_date": "2099-01-01",
            "competition_end_date": "2099-01-03",
            "deadline": "2099-02-01T00:00:00Z",
            "submission_key": submission_key,
            "member_ids": ["2250001"],
            "fee_categories": ["registration"],
            "administrator_id": "admin-1",
            "invoice_title": "同济大学",
            "tax_number": "12100000425006117D",
        }
    )
    task = task_repository.create(
        resolve_task_create(
            payload,
            GlobalInvoiceConfig(invoice_title="同济大学", tax_number="12100000425006117D"),
        )
    )
    task_repository.update_status(task.id, status)
    return task.id


def test_workflow_lists_selects_and_uploads_current_task():
    workflow_service, task_repository, _binding_repository, oauth_service, task_context_repository, upload_service = build_workflow_service()
    open_task_id = create_task(task_repository, submission_key="icpc-final", status=TaskStatus.OPEN)
    create_task(task_repository, submission_key="ccpc-regional", status=TaskStatus.CLOSED)

    authorization = oauth_service.create_authorization(
        telegram_user_id=123456,
        telegram_chat_id=123456,
        telegram_username="tongjicoder",
    )
    oauth_service.confirm_authorization(token=authorization.token, member_id="2250001")

    tasks_text = workflow_service.list_tasks(telegram_user_id=123456)
    assert "icpc-final" in tasks_text
    assert "ccpc-regional" in tasks_text

    select_text = workflow_service.select_task(
        telegram_user_id=123456,
        submission_key="icpc-final",
    )
    assert "已切换当前任务" in select_text
    assert task_context_repository.get_by_telegram_user_id(123456) is not None

    upload_text = workflow_service.upload_invoice(
        telegram_user_id=123456,
        incoming_file=TelegramIncomingFile(
            original_filename="invoice.pdf",
            content_type="application/pdf",
            content=b"fake-pdf",
        ),
        request_id="req-1",
    )
    assert "上传成功" in upload_text
    assert upload_service.calls[0]["task_id"] == open_task_id


def test_workflow_requires_current_task_before_upload():
    workflow_service, _task_repository, _binding_repository, oauth_service, _task_context_repository, _upload_service = build_workflow_service()
    authorization = oauth_service.create_authorization(
        telegram_user_id=123456,
        telegram_chat_id=123456,
        telegram_username="tongjicoder",
    )
    oauth_service.confirm_authorization(token=authorization.token, member_id="2250001")

    upload_text = workflow_service.upload_invoice(
        telegram_user_id=123456,
        incoming_file=TelegramIncomingFile(
            original_filename="invoice.pdf",
            content_type="application/pdf",
            content=b"fake-pdf",
        ),
        request_id="req-2",
    )
    assert "当前还没有选中的任务" in upload_text


def test_workflow_reports_task_not_open_error():
    workflow_service, task_repository, _binding_repository, oauth_service, _task_context_repository, upload_service = build_workflow_service()
    create_task(task_repository, submission_key="icpc-final", status=TaskStatus.CLOSED)
    authorization = oauth_service.create_authorization(
        telegram_user_id=123456,
        telegram_chat_id=123456,
        telegram_username="tongjicoder",
    )
    oauth_service.confirm_authorization(token=authorization.token, member_id="2250001")
    workflow_service.select_task(
        telegram_user_id=123456,
        submission_key="icpc-final",
    )
    upload_service.mode = "task_not_open"

    upload_text = workflow_service.upload_invoice(
        telegram_user_id=123456,
        incoming_file=TelegramIncomingFile(
            original_filename="invoice.pdf",
            content_type="application/pdf",
            content=b"fake-pdf",
        ),
        request_id="req-3",
    )
    assert "现在不接受发票上传" in upload_text
