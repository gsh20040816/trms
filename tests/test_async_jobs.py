from datetime import datetime, timedelta, timezone
from threading import Event, Lock, Thread
from time import monotonic

import pytest

import trms_backend.__main__ as backend_main
import trms_backend.application.email_inbox_polling as email_inbox_polling
from trms_backend.application.export_async_jobs import ExportAsyncJobProcessor
from trms_backend.application.email_inbox_polling import (
    EmailInboxImportProcessor,
    EmailInboxPollingProcessor,
    ImapEmailInboxClient,
    PolledEmailMessage,
    StaticEmailInboxClient,
)
from trms_backend.application.email_material_submission import EmailMaterialSubmissionService
from trms_backend.application.material_submission import MaterialSubmissionService
from trms_backend.application.metrics import InMemoryMetricsCollector
from trms_backend.application.outbound_email import OutboundEmailMessage
import trms_backend.application.recognition_async_jobs as recognition_async_jobs
from trms_backend.application.async_jobs import AsyncJobWorker, AsyncJobWorkerModeError
from trms_backend.application.recognition_async_jobs import RecognitionAsyncJobProcessor
from trms_backend.application.recognition_preparation import (
    RecognitionPreparationService,
    RecognitionTaskExecutionConflictError,
)
from trms_backend.domain.audit_logs import InMemoryAuditLogRepository
from trms_backend.domain.email_bindings import (
    EmailAccountBindingUpsert,
    EmailSubmissionIdentityResolver,
    InMemoryEmailAccountBindingRepository,
)
from trms_backend.domain.email_inbox import (
    EmailInboxRecordCreate,
    EmailInboxRecordStatus,
    InMemoryEmailInboxRecordRepository,
)
from trms_backend.domain.tasks import InMemoryTaskRepository, TaskCreate, TaskStatus
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.domain.materials import InMemoryMaterialRepository
from trms_backend.domain.exports import (
    StoredExportArtifactRecord,
    TaskExportJobRecord,
    TaskExportJobStatus,
    TaskExportVersionSnapshot,
)
from trms_backend.domain.recognitions import RecognitionTaskCreate, RecognitionTaskRecord, RecognitionTaskStatus
from trms_backend.runtime_config import load_runtime_config


class RecordingOutboundEmailSender:
    def __init__(self) -> None:
        self.messages: list[OutboundEmailMessage] = []

    def send(self, message: OutboundEmailMessage) -> None:
        self.messages.append(message)


def build_email_package_bytes(
    *,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> bytes:
    payload = [
        b"From: nested@example.edu\r\n",
        b"Subject: Nested package\r\n",
        b"MIME-Version: 1.0\r\n",
    ]
    if not attachments:
        payload.extend([
            b"Content-Type: text/plain; charset=utf-8\r\n\r\n",
            b"plain body only\r\n",
        ])
        return b"".join(payload)

    payload.append(b"Content-Type: multipart/mixed; boundary=PACKAGE\r\n\r\n")
    payload.extend([
        b"--PACKAGE\r\n",
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n",
        b"nested body\r\n\r\n",
    ])
    for filename, content, content_type in attachments:
        payload.extend([
            b"--PACKAGE\r\n",
            f"Content-Type: {content_type}\r\n".encode("utf-8"),
            f"Content-Disposition: attachment; filename=\"{filename}\"\r\n\r\n".encode("utf-8"),
            content,
            b"\r\n",
        ])
    payload.append(b"--PACKAGE--\r\n")
    return b"".join(payload)


class InMemoryRecognitionTaskRepository:
    def __init__(self) -> None:
        self._items: list[RecognitionTaskCreate] = []

    def create(self, data: RecognitionTaskCreate):
        self._items.append(data)
        return data


class CountingProcessor:
    def __init__(self, job_type: str, processed_count: int) -> None:
        self.job_type = job_type
        self._processed_count = processed_count
        self.calls = 0

    def run_once(self) -> int:
        self.calls += 1
        return self._processed_count


class BlockingProcessor:
    def __init__(self, job_type: str, release: Event) -> None:
        self.job_type = job_type
        self.release = release
        self.started = Event()
        self.finished = Event()
        self.calls = 0

    def run_once(self) -> int:
        self.calls += 1
        self.started.set()
        self.release.wait(timeout=1)
        self.finished.set()
        return 1


class FailingProcessor:
    def __init__(self, job_type: str) -> None:
        self.job_type = job_type

    def run_once(self) -> int:
        raise RuntimeError("processor failed")


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
    assert worker.worker_concurrency == 4
    assert result.processed_counts == {"recognition": 2, "export": 1}
    assert result.total_processed == 3


def test_async_job_worker_times_out_blocking_processors_without_restarting_them():
    config = load_runtime_config(
        env={},
        async_job_mode="worker",
        async_job_worker_task_timeout_seconds=0.03,
    )
    release = Event()
    blocking_processor = BlockingProcessor("recognition", release)
    fast_processor = CountingProcessor("export", 2)
    worker = AsyncJobWorker(
        config.async_jobs,
        processors=(blocking_processor, fast_processor),
    )

    started_at = monotonic()
    first_result = worker.run_once()
    elapsed_seconds = monotonic() - started_at
    second_result = worker.run_once()

    release.set()
    assert blocking_processor.finished.wait(timeout=1)
    assert blocking_processor.started.is_set()
    assert elapsed_seconds < 0.5
    assert blocking_processor.calls == 1
    assert fast_processor.calls == 2
    assert first_result.processed_counts == {"recognition": 0, "export": 2}
    assert second_result.processed_counts == {"recognition": 0, "export": 2}


def test_async_job_worker_isolates_processor_failures():
    config = load_runtime_config(
        env={},
        async_job_mode="worker",
        async_job_worker_task_timeout_seconds=0.1,
    )
    worker = AsyncJobWorker(
        config.async_jobs,
        processors=(
            FailingProcessor("recognition"),
            CountingProcessor("export", 1),
        ),
    )

    result = worker.run_once()

    assert result.processed_counts == {"recognition": 0, "export": 1}
    assert result.total_processed == 1


def test_resolve_recognition_worker_max_workers_serializes_sqlite():
    assert backend_main._resolve_recognition_worker_max_workers("sqlite:///./trms.db", 4) == 1
    assert backend_main._resolve_recognition_worker_max_workers(" sqlite:///./trms.db ", 2) == 1
    assert backend_main._resolve_recognition_worker_max_workers("postgresql+psycopg://db/trms", 4) == 4
    assert backend_main._resolve_recognition_worker_max_workers("postgresql+psycopg://db/trms", 1) == 1


def test_async_job_worker_run_once_emits_iteration_logs(monkeypatch):
    config = load_runtime_config(env={}, async_job_mode="worker")
    worker = AsyncJobWorker(
        config.async_jobs,
        processors=(CountingProcessor("recognition", 2),),
    )
    entries: list[str] = []
    monkeypatch.setattr(
        "trms_backend.application.async_jobs.LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: entries.append(f"{message} {payload}"),
            },
        )(),
    )

    worker.run_once()

    assert any("worker_poll_start" in entry for entry in entries)
    assert any("worker_poll_complete" in entry for entry in entries)
    assert any("'worker_concurrency': 4" in entry for entry in entries)
    assert any("'processed_counts': {'recognition': 2}" in entry for entry in entries)


def test_async_job_worker_run_forever_logs_idle_wait(monkeypatch):
    config = load_runtime_config(env={}, async_job_mode="worker")

    def stop_sleep(_seconds: float) -> None:
        raise StopIteration

    worker = AsyncJobWorker(
        config.async_jobs,
        processors=(CountingProcessor("recognition", 0),),
        sleep=stop_sleep,
    )
    entries: list[str] = []
    monkeypatch.setattr(
        "trms_backend.application.async_jobs.LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: entries.append(f"{message} {payload}"),
            },
        )(),
    )

    try:
        worker.run_forever()
    except StopIteration:
        pass
    else:  # pragma: no cover - defensive branch
        raise AssertionError("expected custom sleep to stop the worker loop")

    assert any("worker_idle_wait" in entry for entry in entries)
    assert any("'sleep_seconds': 5.0" in entry for entry in entries)


def test_async_job_worker_rejects_in_process_mode():
    config = load_runtime_config(env={})
    worker = AsyncJobWorker(config.async_jobs)

    try:
        worker.run_once()
    except AsyncJobWorkerModeError as error:
        assert error.mode == "in_process"
    else:  # pragma: no cover - defensive branch
        raise AssertionError("expected worker mode validation to fail")


def test_email_inbox_polling_processor_records_ready_and_ignored_messages(tmp_path):
    task_repository = InMemoryTaskRepository()
    task = task_repository.create(
        TaskCreate(
            competition_name="ICPC Mail Task",
            competition_location="Shanghai",
            competition_start_date=datetime(2026, 11, 1, tzinfo=timezone.utc).date(),
            competition_end_date=datetime(2026, 11, 3, tzinfo=timezone.utc).date(),
            deadline=datetime.now(timezone.utc) + timedelta(days=7),
            email_submission_key="icpc-mail-task",
            member_ids=["2250001"],
            fee_categories=["registration"],
            administrator_id="admin-1",
            administrator_ids=["admin-1"],
            project_info="",
            reimburser_info="",
            invoice_title="同济大学",
            tax_number="91310000TEST00001",
        )
    )
    task_repository.update_status(task.id, TaskStatus.OPEN)

    binding_repository = InMemoryEmailAccountBindingRepository()
    binding_repository.upsert(
        EmailAccountBindingUpsert(member_id="2250001", email="bound@tongji.edu.cn")
    )
    inbox_repository = InMemoryEmailInboxRecordRepository()
    audit_repository = InMemoryAuditLogRepository()
    client = StaticEmailInboxClient(
        [
            PolledEmailMessage(
                mailbox_uid="1",
                message_id="<a@example.edu>",
                sender_email="bound@tongji.edu.cn",
                subject="<icpc-mail-task>Fw: invoice",
                body="正文内容不参与结构化解析。",
                raw_bytes=b"raw-message-1",
                received_at=datetime.now(timezone.utc),
            ),
            PolledEmailMessage(
                mailbox_uid="2",
                message_id="<b@example.edu>",
                sender_email="unknown@tongji.edu.cn",
                subject="<icpc-mail-task>Fw: invoice",
                body="正文内容不参与结构化解析。",
                raw_bytes=b"raw-message-2",
                received_at=datetime.now(timezone.utc),
            ),
        ]
    )
    processor = EmailInboxPollingProcessor(
        email_inbox_client=client,
        email_inbox_record_repository=inbox_repository,
        email_submission_identity_resolver=EmailSubmissionIdentityResolver(binding_repository),
        task_repository=task_repository,
        raw_email_storage=LocalMaterialFileStorage(tmp_path / "email-inbox"),
        audit_log_repository=audit_repository,
    )

    processed = processor.run_once()

    assert processed == 2
    ready_items = inbox_repository.list_ready_for_import(limit=10)
    assert len(ready_items) == 1
    assert ready_items[0].mailbox_uid == "1"
    assert ready_items[0].result_code == "ready_for_import"
    ignored = inbox_repository.get_by_mailbox_uid("2")
    assert ignored is not None
    assert ignored.result_code == "ignored_unbound_sender"


def test_email_inbox_polling_processor_skips_duplicate_mailbox_uid(tmp_path):
    task_repository = InMemoryTaskRepository()
    binding_repository = InMemoryEmailAccountBindingRepository()
    inbox_repository = InMemoryEmailInboxRecordRepository()
    audit_repository = InMemoryAuditLogRepository()
    client = StaticEmailInboxClient(
        [
            PolledEmailMessage(
                mailbox_uid="dup-1",
                message_id="<dup@example.edu>",
                sender_email="unknown@tongji.edu.cn",
                subject="<missing-task>Fw: upload",
                body="任意正文",
                raw_bytes=b"dup-message",
                received_at=datetime.now(timezone.utc),
            )
        ]
    )
    processor = EmailInboxPollingProcessor(
        email_inbox_client=client,
        email_inbox_record_repository=inbox_repository,
        email_submission_identity_resolver=EmailSubmissionIdentityResolver(binding_repository),
        task_repository=task_repository,
        raw_email_storage=LocalMaterialFileStorage(tmp_path / "email-inbox"),
        audit_log_repository=audit_repository,
    )

    assert processor.run_once() == 1
    assert processor.run_once() == 0


def test_static_email_inbox_client_only_returns_messages_after_last_seen_uid():
    client = StaticEmailInboxClient(
        [
            PolledEmailMessage(
                mailbox_uid="10",
                message_id=None,
                sender_email="a@example.edu",
                subject="a",
                body="",
                raw_bytes=b"a",
                received_at=None,
            ),
            PolledEmailMessage(
                mailbox_uid="11",
                message_id=None,
                sender_email="b@example.edu",
                subject="b",
                body="",
                raw_bytes=b"b",
                received_at=None,
            ),
        ]
    )

    result = client.fetch_new_messages(after_uid="10")

    assert [item.mailbox_uid for item in result] == ["11"]


@pytest.mark.parametrize(
    ("use_ssl", "constructor_name"),
    [(True, "IMAP4_SSL"), (False, "IMAP4")],
)
def test_imap_email_inbox_client_applies_socket_timeout(
    monkeypatch,
    use_ssl,
    constructor_name,
):
    captured: dict[str, object] = {}

    class RecordingImapConnection:
        def __init__(self, host, port, *, timeout):
            captured.update(host=host, port=port, timeout=timeout)

        def login(self, username, password):
            captured.update(username=username, password=password)

        def select(self, mailbox):
            captured["mailbox"] = mailbox

        def uid(self, command, charset, search_criteria):
            captured.update(
                command=command,
                charset=charset,
                search_criteria=search_criteria,
            )
            return "OK", [b""]

        def logout(self):
            captured["logged_out"] = True

    monkeypatch.setattr(
        email_inbox_polling.imaplib,
        constructor_name,
        RecordingImapConnection,
    )
    config = load_runtime_config(
        env={
            "TRMS_IMAP_HOST": "imap.example.edu",
            "TRMS_IMAP_PORT": "993",
            "TRMS_IMAP_USERNAME": "mailer@example.edu",
            "TRMS_IMAP_PASSWORD": "imap-secret",
            "TRMS_IMAP_TIMEOUT_SECONDS": "12",
            "TRMS_IMAP_USE_SSL": str(use_ssl).lower(),
        }
    )
    assert config.email_inbox is not None

    result = ImapEmailInboxClient(config.email_inbox).fetch_new_messages(after_uid="10")

    assert result == []
    assert captured == {
        "host": "imap.example.edu",
        "port": 993,
        "timeout": 12,
        "username": "mailer@example.edu",
        "password": "imap-secret",
        "mailbox": "INBOX",
        "command": "search",
        "charset": None,
        "search_criteria": "UID 10:*",
        "logged_out": True,
    }


def test_email_inbox_polling_processor_ignores_bound_sender_with_unknown_task_key(tmp_path):
    task_repository = InMemoryTaskRepository()
    binding_repository = InMemoryEmailAccountBindingRepository()
    binding_repository.upsert(
        EmailAccountBindingUpsert(member_id="2250001", email="bound@tongji.edu.cn")
    )
    inbox_repository = InMemoryEmailInboxRecordRepository()
    audit_repository = InMemoryAuditLogRepository()
    client = StaticEmailInboxClient(
        [
            PolledEmailMessage(
                mailbox_uid="missing-task-1",
                message_id="<missing@example.edu>",
                sender_email="bound@tongji.edu.cn",
                subject="<missing-task>Fw: upload",
                body="任意正文",
                raw_bytes=b"missing-task-message",
                received_at=datetime.now(timezone.utc),
            )
        ]
    )
    processor = EmailInboxPollingProcessor(
        email_inbox_client=client,
        email_inbox_record_repository=inbox_repository,
        email_submission_identity_resolver=EmailSubmissionIdentityResolver(binding_repository),
        task_repository=task_repository,
        raw_email_storage=LocalMaterialFileStorage(tmp_path / "email-inbox"),
        audit_log_repository=audit_repository,
    )

    assert processor.run_once() == 1
    record = inbox_repository.get_by_mailbox_uid("missing-task-1")
    assert record is not None
    assert record.result_code == "ignored_unknown_task_key"


def test_email_inbox_polling_processor_ignores_invalid_sender_email_without_crashing(tmp_path):
    task_repository = InMemoryTaskRepository()
    binding_repository = InMemoryEmailAccountBindingRepository()
    inbox_repository = InMemoryEmailInboxRecordRepository()
    audit_repository = InMemoryAuditLogRepository()
    client = StaticEmailInboxClient(
        [
            PolledEmailMessage(
                mailbox_uid="invalid-sender-1",
                message_id="<invalid@example.edu>",
                sender_email="invalid sender",
                subject="<anything>Fw: upload",
                body="任意正文",
                raw_bytes=b"invalid-sender-message",
                received_at=datetime.now(timezone.utc),
            )
        ]
    )
    processor = EmailInboxPollingProcessor(
        email_inbox_client=client,
        email_inbox_record_repository=inbox_repository,
        email_submission_identity_resolver=EmailSubmissionIdentityResolver(binding_repository),
        task_repository=task_repository,
        raw_email_storage=LocalMaterialFileStorage(tmp_path / "email-inbox"),
        audit_log_repository=audit_repository,
    )

    assert processor.run_once() == 1
    record = inbox_repository.get_by_mailbox_uid("invalid-sender-1")
    assert record is not None
    assert record.status == EmailInboxRecordStatus.IGNORED
    assert record.result_code == "ignored_invalid_sender_email"


def test_email_inbox_import_processor_submits_attachment_and_sends_receipt(tmp_path):
    task_repository = InMemoryTaskRepository()
    task = task_repository.create(
        TaskCreate(
            competition_name="ICPC Mail Task",
            competition_location="Shanghai",
            competition_start_date=datetime(2026, 11, 1, tzinfo=timezone.utc).date(),
            competition_end_date=datetime(2026, 11, 3, tzinfo=timezone.utc).date(),
            deadline=datetime.now(timezone.utc) + timedelta(days=7),
            email_submission_key="icpc-mail-task",
            member_ids=["2250001"],
            fee_categories=["registration"],
            administrator_id="admin-1",
            administrator_ids=["admin-1"],
            project_info="",
            reimburser_info="",
            invoice_title="同济大学",
            tax_number="91310000TEST00001",
        )
    )
    task_repository.update_status(task.id, TaskStatus.OPEN)
    material_repository = InMemoryMaterialRepository()
    recognition_task_repository = InMemoryRecognitionTaskRepository()
    audit_repository = InMemoryAuditLogRepository()
    material_storage = LocalMaterialFileStorage(tmp_path / "materials")
    inbox_storage = LocalMaterialFileStorage(tmp_path / "emails")
    binding_repository = InMemoryEmailAccountBindingRepository()
    binding_repository.upsert(
        EmailAccountBindingUpsert(member_id="2250001", email="bound@tongji.edu.cn")
    )
    email_material_submission_service = EmailMaterialSubmissionService(
        material_submission_service=MaterialSubmissionService(
            task_repository,
            material_repository,
            material_storage,
            recognition_task_repository,
            audit_repository,
        ),
        task_repository=task_repository,
        submission_identity_resolver=EmailSubmissionIdentityResolver(binding_repository),
    )
    inbox_repository = InMemoryEmailInboxRecordRepository()
    raw_email = (
        b"From: bound@tongji.edu.cn\r\n"
        b"Subject: <icpc-mail-task>Fw: invoice\r\n"
        b"MIME-Version: 1.0\r\n"
        b"Content-Type: multipart/mixed; boundary=BOUNDARY\r\n\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"\xe8\xbf\x99\xe9\x87\x8c\xe6\x98\xaf\xe8\x87\xaa\xe7\x94\xb1\xe6\xad\xa3\xe6\x96\x87\xe3\x80\x82\r\n\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: application/pdf\r\n"
        b"Content-Disposition: attachment; filename=\"invoice.pdf\"\r\n\r\n"
        b"fake-pdf-content\r\n"
        b"--BOUNDARY--\r\n"
    )
    stored_raw = inbox_storage.save(
        task_id="_email_inbox",
        original_filename="1.eml",
        content_type="message/rfc822",
        content=raw_email,
    )
    record = inbox_repository.create(
        EmailInboxRecordCreate(
            mailbox_uid="1",
            message_id="<a@example.edu>",
            sender_email="bound@tongji.edu.cn",
            subject="<icpc-mail-task>Fw: invoice",
            raw_storage_key=stored_raw.storage_key,
            received_at=datetime.now(timezone.utc),
            status=EmailInboxRecordStatus.READY_FOR_IMPORT,
            result_code="ready_for_import",
            resolved_member_id="2250001",
            submitted_task_key="icpc-mail-task",
            resolved_task_id=task.id,
        )
    )
    sender = RecordingOutboundEmailSender()
    processor = EmailInboxImportProcessor(
        email_inbox_record_repository=inbox_repository,
        raw_email_storage=inbox_storage,
        email_material_submission_service=email_material_submission_service,
        outbound_email_sender=sender,
        audit_log_repository=audit_repository,
    )

    assert processor.run_once() == 1
    updated = inbox_repository.get(record.id)
    assert updated is not None
    assert updated.status == EmailInboxRecordStatus.IMPORTED
    assert updated.result_code == "imported"
    materials = material_repository.list_by_task(task.id)
    assert len(materials) == 1
    assert materials[0].material_type.value == "other_attachment"
    assert sender.messages[-1].subject == "TRMS 邮件材料已收到"
    assert sender.messages[-1].text_body == (
        "你的邮件材料已收到并进入任务处理链路。\n"
        "成功附件数：1\n"
        "成功附件：\n"
        "- invoice.pdf\n"
    )


def test_email_inbox_import_processor_marks_missing_attachment_as_failed(tmp_path):
    inbox_repository = InMemoryEmailInboxRecordRepository()
    audit_repository = InMemoryAuditLogRepository()
    sender = RecordingOutboundEmailSender()
    inbox_storage = LocalMaterialFileStorage(tmp_path / "emails")
    raw_email = (
        b"From: bound@tongji.edu.cn\r\n"
        b"Subject: <icpc-mail-task>Fw: invoice\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"\xe6\xb2\xa1\xe6\x9c\x89\xe9\x99\x84\xe4\xbb\xb6\xe7\x9a\x84\xe9\x82\xae\xe4\xbb\xb6\r\n"
    )
    stored_raw = inbox_storage.save(
        task_id="_email_inbox",
        original_filename="2.eml",
        content_type="message/rfc822",
        content=raw_email,
    )
    record = inbox_repository.create(
        EmailInboxRecordCreate(
            mailbox_uid="2",
            message_id="<b@example.edu>",
            sender_email="bound@tongji.edu.cn",
            subject="<icpc-mail-task>Fw: invoice",
            raw_storage_key=stored_raw.storage_key,
            received_at=datetime.now(timezone.utc),
            status=EmailInboxRecordStatus.READY_FOR_IMPORT,
            result_code="ready_for_import",
            resolved_member_id="2250001",
            submitted_task_key="icpc-mail-task",
            resolved_task_id="task-1",
        )
    )
    processor = EmailInboxImportProcessor(
        email_inbox_record_repository=inbox_repository,
        raw_email_storage=inbox_storage,
        email_material_submission_service=EmailMaterialSubmissionService(
            material_submission_service=MaterialSubmissionService(
                InMemoryTaskRepository(),
                InMemoryMaterialRepository(),
                LocalMaterialFileStorage(tmp_path / "materials"),
                InMemoryRecognitionTaskRepository(),
                audit_repository,
            ),
            task_repository=InMemoryTaskRepository(),
            submission_identity_resolver=None,
        ),
        outbound_email_sender=sender,
        audit_log_repository=audit_repository,
    )

    assert processor.run_once() == 1
    updated = inbox_repository.get(record.id)
    assert updated is not None
    assert updated.status == EmailInboxRecordStatus.IMPORT_FAILED
    assert updated.result_code == "missing_attachments"
    assert sender.messages[-1].subject == "TRMS 邮件材料处理失败"
    assert sender.messages[-1].text_body == (
        "你的邮件材料未成功进入任务处理链路。\n"
        "失败原因：missing_attachments\n"
        "失败附件：无\n"
    )


def test_email_inbox_import_processor_does_not_read_ignored_invalid_subject_record(tmp_path):
    inbox_repository = InMemoryEmailInboxRecordRepository()
    audit_repository = InMemoryAuditLogRepository()
    sender = RecordingOutboundEmailSender()
    inbox_storage = LocalMaterialFileStorage(tmp_path / "emails")
    raw_email = (
        b"From: bound@tongji.edu.cn\r\n"
        b"Subject: hello world\r\n"
        b"MIME-Version: 1.0\r\n"
        b"Content-Type: multipart/mixed; boundary=BOUNDARY\r\n\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: application/pdf\r\n"
        b"Content-Disposition: attachment; filename=\"invoice.pdf\"\r\n\r\n"
        b"fake-pdf-content\r\n"
        b"--BOUNDARY--\r\n"
    )
    stored_raw = inbox_storage.save(
        task_id="_email_inbox",
        original_filename="ignored.eml",
        content_type="message/rfc822",
        content=raw_email,
    )
    record = inbox_repository.create(
        EmailInboxRecordCreate(
            mailbox_uid="ignored-1",
            message_id="<ignored@example.edu>",
            sender_email="bound@tongji.edu.cn",
            subject="hello world",
            raw_storage_key=stored_raw.storage_key,
            received_at=datetime.now(timezone.utc),
            status=EmailInboxRecordStatus.IGNORED,
            result_code="invalid_subject_prefix",
            resolved_member_id="2250001",
            submitted_task_key=None,
            resolved_task_id=None,
        )
    )
    processor = EmailInboxImportProcessor(
        email_inbox_record_repository=inbox_repository,
        raw_email_storage=inbox_storage,
        email_material_submission_service=EmailMaterialSubmissionService(
            material_submission_service=MaterialSubmissionService(
                InMemoryTaskRepository(),
                InMemoryMaterialRepository(),
                LocalMaterialFileStorage(tmp_path / "materials"),
                InMemoryRecognitionTaskRepository(),
                audit_repository,
            ),
            task_repository=InMemoryTaskRepository(),
            submission_identity_resolver=None,
        ),
        outbound_email_sender=sender,
        audit_log_repository=audit_repository,
    )

    assert processor.run_once() == 0
    updated = inbox_repository.get(record.id)
    assert updated is not None
    assert updated.status == EmailInboxRecordStatus.IGNORED
    assert sender.messages == []


def test_email_inbox_import_processor_marks_partial_success_and_sends_partial_receipt(tmp_path):
    task_repository = InMemoryTaskRepository()
    task = task_repository.create(
        TaskCreate(
            competition_name="ICPC Mail Task",
            competition_location="Shanghai",
            competition_start_date=datetime(2026, 11, 1, tzinfo=timezone.utc).date(),
            competition_end_date=datetime(2026, 11, 3, tzinfo=timezone.utc).date(),
            deadline=datetime.now(timezone.utc) + timedelta(days=7),
            email_submission_key="icpc-mail-task",
            member_ids=["2250001"],
            fee_categories=["registration"],
            administrator_id="admin-1",
            administrator_ids=["admin-1"],
            project_info="",
            reimburser_info="",
            invoice_title="同济大学",
            tax_number="91310000TEST00001",
        )
    )
    task_repository.update_status(task.id, TaskStatus.OPEN)
    material_repository = InMemoryMaterialRepository()
    recognition_task_repository = InMemoryRecognitionTaskRepository()
    audit_repository = InMemoryAuditLogRepository()
    material_storage = LocalMaterialFileStorage(tmp_path / "materials")
    inbox_storage = LocalMaterialFileStorage(tmp_path / "emails")
    binding_repository = InMemoryEmailAccountBindingRepository()
    binding_repository.upsert(
        EmailAccountBindingUpsert(member_id="2250001", email="bound@tongji.edu.cn")
    )
    email_material_submission_service = EmailMaterialSubmissionService(
        material_submission_service=MaterialSubmissionService(
            task_repository,
            material_repository,
            material_storage,
            recognition_task_repository,
            audit_repository,
        ),
        task_repository=task_repository,
        submission_identity_resolver=EmailSubmissionIdentityResolver(binding_repository),
    )
    inbox_repository = InMemoryEmailInboxRecordRepository()
    raw_email = (
        b"From: bound@tongji.edu.cn\r\n"
        b"Subject: <icpc-mail-task>Fw: invoice\r\n"
        b"MIME-Version: 1.0\r\n"
        b"Content-Type: multipart/mixed; boundary=BOUNDARY\r\n\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"\xe6\xad\xa3\xe6\x96\x87\xe4\xb8\x8d\xe9\x9c\x80\xe8\xa6\x81\xe5\x9b\xba\xe5\xae\x9a\xe6\xa0\xbc\xe5\xbc\x8f\xe3\x80\x82\r\n\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: application/pdf\r\n"
        b"Content-Disposition: attachment; filename=\"invoice.pdf\"\r\n\r\n"
        b"fake-pdf-content\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: application/pdf\r\n"
        b"Content-Disposition: attachment; filename=\"   \"\r\n\r\n"
        b"bad-file\r\n"
        b"--BOUNDARY--\r\n"
    )
    stored_raw = inbox_storage.save(
        task_id="_email_inbox",
        original_filename="3.eml",
        content_type="message/rfc822",
        content=raw_email,
    )
    record = inbox_repository.create(
        EmailInboxRecordCreate(
            mailbox_uid="3",
            message_id="<c@example.edu>",
            sender_email="bound@tongji.edu.cn",
            subject="<icpc-mail-task>Fw: invoice",
            raw_storage_key=stored_raw.storage_key,
            received_at=datetime.now(timezone.utc),
            status=EmailInboxRecordStatus.READY_FOR_IMPORT,
            result_code="ready_for_import",
            resolved_member_id="2250001",
            submitted_task_key="icpc-mail-task",
            resolved_task_id=task.id,
        )
    )
    sender = RecordingOutboundEmailSender()
    processor = EmailInboxImportProcessor(
        email_inbox_record_repository=inbox_repository,
        raw_email_storage=inbox_storage,
        email_material_submission_service=email_material_submission_service,
        outbound_email_sender=sender,
        audit_log_repository=audit_repository,
    )

    assert processor.run_once() == 1
    updated = inbox_repository.get(record.id)
    assert updated is not None
    assert updated.status == EmailInboxRecordStatus.PARTIALLY_IMPORTED
    assert updated.result_code == "partially_imported"
    assert sender.messages[-1].subject == "TRMS 邮件材料部分成功"
    assert sender.messages[-1].text_body == (
        "你的邮件材料已部分进入任务处理链路。\n"
        "成功附件数：1\n"
        "失败附件数：1\n"
        "成功附件：\n"
        "- invoice.pdf\n"
        "失败附件：\n"
        "- <unnamed>\n"
    )


def test_email_inbox_import_processor_expands_nested_eml_attachment(tmp_path):
    task_repository = InMemoryTaskRepository()
    task = task_repository.create(
        TaskCreate(
            competition_name="ICPC Mail Task",
            competition_location="Shanghai",
            competition_start_date=datetime(2026, 11, 1, tzinfo=timezone.utc).date(),
            competition_end_date=datetime(2026, 11, 3, tzinfo=timezone.utc).date(),
            deadline=datetime.now(timezone.utc) + timedelta(days=7),
            email_submission_key="icpc-mail-task",
            member_ids=["2250001"],
            fee_categories=["registration"],
            administrator_id="admin-1",
            administrator_ids=["admin-1"],
            project_info="",
            reimburser_info="",
            invoice_title="同济大学",
            tax_number="91310000TEST00001",
        )
    )
    task_repository.update_status(task.id, TaskStatus.OPEN)
    material_repository = InMemoryMaterialRepository()
    recognition_task_repository = InMemoryRecognitionTaskRepository()
    audit_repository = InMemoryAuditLogRepository()
    material_storage = LocalMaterialFileStorage(tmp_path / "materials")
    inbox_storage = LocalMaterialFileStorage(tmp_path / "emails")
    binding_repository = InMemoryEmailAccountBindingRepository()
    binding_repository.upsert(
        EmailAccountBindingUpsert(member_id="2250001", email="bound@tongji.edu.cn")
    )
    email_material_submission_service = EmailMaterialSubmissionService(
        material_submission_service=MaterialSubmissionService(
            task_repository,
            material_repository,
            material_storage,
            recognition_task_repository,
            audit_repository,
        ),
        task_repository=task_repository,
        submission_identity_resolver=EmailSubmissionIdentityResolver(binding_repository),
    )
    inner_eml = build_email_package_bytes(
        attachments=[("invoice.pdf", b"inner-pdf-content", "application/pdf")]
    )
    inbox_repository = InMemoryEmailInboxRecordRepository()
    raw_email = (
        b"From: bound@tongji.edu.cn\r\n"
        b"Subject: <icpc-mail-task>Fw: package\r\n"
        b"MIME-Version: 1.0\r\n"
        b"Content-Type: multipart/mixed; boundary=BOUNDARY\r\n\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"\xe6\xad\xa3\xe6\x96\x87\xe6\x90\xba\xe5\xb8\xa6 eml \xe9\x99\x84\xe4\xbb\xb6\xe3\x80\x82\r\n\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: message/rfc822\r\n"
        b"Content-Disposition: attachment; filename=\"forwarded.eml\"\r\n\r\n"
        + inner_eml
        + b"\r\n--BOUNDARY--\r\n"
    )
    stored_raw = inbox_storage.save(
        task_id="_email_inbox",
        original_filename="4.eml",
        content_type="message/rfc822",
        content=raw_email,
    )
    record = inbox_repository.create(
        EmailInboxRecordCreate(
            mailbox_uid="4",
            message_id="<d@example.edu>",
            sender_email="bound@tongji.edu.cn",
            subject="<icpc-mail-task>Fw: package",
            raw_storage_key=stored_raw.storage_key,
            received_at=datetime.now(timezone.utc),
            status=EmailInboxRecordStatus.READY_FOR_IMPORT,
            result_code="ready_for_import",
            resolved_member_id="2250001",
            submitted_task_key="icpc-mail-task",
            resolved_task_id=task.id,
        )
    )
    sender = RecordingOutboundEmailSender()
    processor = EmailInboxImportProcessor(
        email_inbox_record_repository=inbox_repository,
        raw_email_storage=inbox_storage,
        email_material_submission_service=email_material_submission_service,
        outbound_email_sender=sender,
        audit_log_repository=audit_repository,
    )

    assert processor.run_once() == 1
    updated = inbox_repository.get(record.id)
    assert updated is not None
    assert updated.status == EmailInboxRecordStatus.IMPORTED
    assert updated.result_code == "imported"
    materials = material_repository.list_by_task(task.id)
    assert [material.original_filename for material in materials] == ["invoice.pdf"]
    assert sender.messages[-1].subject == "TRMS 邮件材料已收到"


def test_email_inbox_import_processor_normalizes_octet_stream_pdf_attachment(tmp_path):
    task_repository = InMemoryTaskRepository()
    task = task_repository.create(
        TaskCreate(
            competition_name="ICPC Mail Task",
            competition_location="Shanghai",
            competition_start_date=datetime(2026, 11, 1, tzinfo=timezone.utc).date(),
            competition_end_date=datetime(2026, 11, 3, tzinfo=timezone.utc).date(),
            deadline=datetime.now(timezone.utc) + timedelta(days=7),
            email_submission_key="icpc-mail-task",
            member_ids=["2250001"],
            fee_categories=["registration"],
            administrator_id="admin-1",
            administrator_ids=["admin-1"],
            project_info="",
            reimburser_info="",
            invoice_title="同济大学",
            tax_number="91310000TEST00001",
        )
    )
    task_repository.update_status(task.id, TaskStatus.OPEN)
    material_repository = InMemoryMaterialRepository()
    recognition_task_repository = InMemoryRecognitionTaskRepository()
    audit_repository = InMemoryAuditLogRepository()
    material_storage = LocalMaterialFileStorage(tmp_path / "materials")
    inbox_storage = LocalMaterialFileStorage(tmp_path / "emails")
    binding_repository = InMemoryEmailAccountBindingRepository()
    binding_repository.upsert(
        EmailAccountBindingUpsert(member_id="2250001", email="bound@tongji.edu.cn")
    )
    email_material_submission_service = EmailMaterialSubmissionService(
        material_submission_service=MaterialSubmissionService(
            task_repository,
            material_repository,
            material_storage,
            recognition_task_repository,
            audit_repository,
        ),
        task_repository=task_repository,
        submission_identity_resolver=EmailSubmissionIdentityResolver(binding_repository),
    )
    inbox_repository = InMemoryEmailInboxRecordRepository()
    raw_email = (
        b"From: bound@tongji.edu.cn\r\n"
        b"Subject: <icpc-mail-task>Fw: package\r\n"
        b"MIME-Version: 1.0\r\n"
        b"Content-Type: multipart/mixed; boundary=BOUNDARY\r\n\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: application/octet-stream\r\n"
        b"Content-Disposition: attachment; filename=\"hotel-invoice.pdf\"\r\n\r\n"
        b"fake-pdf-content\r\n"
        b"--BOUNDARY--\r\n"
    )
    stored_raw = inbox_storage.save(
        task_id="_email_inbox",
        original_filename="5.eml",
        content_type="message/rfc822",
        content=raw_email,
    )
    record = inbox_repository.create(
        EmailInboxRecordCreate(
            mailbox_uid="5",
            message_id="<e@example.edu>",
            sender_email="bound@tongji.edu.cn",
            subject="<icpc-mail-task>Fw: package",
            raw_storage_key=stored_raw.storage_key,
            received_at=datetime.now(timezone.utc),
            status=EmailInboxRecordStatus.READY_FOR_IMPORT,
            result_code="ready_for_import",
            resolved_member_id="2250001",
            submitted_task_key="icpc-mail-task",
            resolved_task_id=task.id,
        )
    )
    sender = RecordingOutboundEmailSender()
    processor = EmailInboxImportProcessor(
        email_inbox_record_repository=inbox_repository,
        raw_email_storage=inbox_storage,
        email_material_submission_service=email_material_submission_service,
        outbound_email_sender=sender,
        audit_log_repository=audit_repository,
    )

    assert processor.run_once() == 1
    updated = inbox_repository.get(record.id)
    assert updated is not None
    assert updated.status == EmailInboxRecordStatus.IMPORTED
    materials = material_repository.list_by_task(task.id)
    assert len(materials) == 1
    assert materials[0].original_filename == "hotel-invoice.pdf"
    assert materials[0].content_type == "application/pdf"


def test_backend_main_worker_once_uses_worker_entry(monkeypatch):
    config = load_runtime_config(
        env={},
        async_job_mode="worker",
        llm_api_key="sk-secret",
        llm_model="gpt-4.1-mini",
    )
    calls: list[str] = []

    class FakeWorker:
        mode = "worker"
        poll_interval_seconds = 5.0
        worker_concurrency = 4
        worker_task_timeout_seconds = 300.0
        registered_job_types = ("email_inbox", "recognition", "export")

        def run_once(self) -> None:
            calls.append("run_once")

    monkeypatch.setattr(backend_main, "load_runtime_config", lambda **_: config)
    monkeypatch.setattr(backend_main, "load_runtime_environment_variables", lambda: {})
    monkeypatch.setattr(backend_main, "build_async_job_worker", lambda runtime_config: FakeWorker())
    entries: list[str] = []
    monkeypatch.setattr(
        backend_main,
        "LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: entries.append(f"{message} {payload}"),
            },
        )(),
    )

    exit_code = backend_main.main(["worker", "--once"])

    assert exit_code == 0
    assert calls == ["run_once"]


def test_build_async_job_worker_serializes_recognition_threads_for_sqlite(tmp_path, monkeypatch):
    config = load_runtime_config(
        environment="test",
        database_url=f"sqlite:///{tmp_path}/test.db",
        material_storage_dir=tmp_path / "material-storage",
        cors_allowed_origins="http://127.0.0.1:5173",
        public_api_base_url="http://127.0.0.1:8000/api",
        api_host="127.0.0.1",
        api_port=8000,
        async_job_mode="worker",
        async_job_worker_concurrency=4,
    )
    warnings: list[str] = []
    monkeypatch.setattr(
        backend_main,
        "LOGGER",
        type(
            "Logger",
            (),
            {
                "warning": lambda self, message, payload: warnings.append(f"{message} {payload}"),
            },
        )(),
    )

    worker, _ = backend_main.build_async_job_worker(config)

    recognition_processor = next(
        processor
        for processor in worker._processors
        if isinstance(processor, RecognitionAsyncJobProcessor)
    )
    assert recognition_processor.max_workers == 1
    assert any("recognition_worker_sqlite_serialized" in entry for entry in warnings)


def test_worker_entry_configures_info_logging(monkeypatch):
    basic_config_calls: list[dict[str, object]] = []
    config = load_runtime_config(env={}, async_job_mode="worker")

    class FakeWorker:
        mode = "worker"
        poll_interval_seconds = 5.0
        worker_concurrency = 4
        worker_task_timeout_seconds = 300.0
        registered_job_types = ("email_inbox", "recognition")

        def run_once(self) -> None:
            return None

    monkeypatch.setattr(backend_main, "load_runtime_config", lambda **_: config)
    monkeypatch.setattr(backend_main, "load_runtime_environment_variables", lambda: {})
    monkeypatch.setattr(backend_main, "build_async_job_worker", lambda runtime_config: FakeWorker())
    monkeypatch.setattr(
        backend_main.logging,
        "basicConfig",
        lambda **kwargs: basic_config_calls.append(kwargs),
    )

    exit_code = backend_main.main(["worker", "--once"])

    assert exit_code == 0
    assert basic_config_calls == [
        {
            "level": backend_main.logging.INFO,
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "force": False,
        }
    ]


def test_backend_main_keeps_legacy_api_entrypoint(monkeypatch):
    config = load_runtime_config(env={})
    uvicorn_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        backend_main,
        "load_runtime_config",
        lambda api_host=None, api_port=None, env=None: config,
    )
    monkeypatch.setattr(backend_main, "load_runtime_environment_variables", lambda: {})
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


def test_backend_main_telegram_bot_entry_uses_polling_runner(monkeypatch):
    config = load_runtime_config(
        env={},
        public_web_base_url="http://127.0.0.1:5173",
        telegram_bot_token="telegram-secret-token",
    )
    calls: list[bool] = []
    log_entries: list[str] = []

    class FakeTelegramProcessor:
        async def run_polling(self, *, drop_pending_updates: bool = False) -> None:
            calls.append(drop_pending_updates)

    fake_app = type(
        "FakeApp",
        (),
        {"state": type("State", (), {"telegram_webhook_processor": FakeTelegramProcessor()})()},
    )()

    monkeypatch.setattr(backend_main, "load_runtime_config", lambda **_: config)
    monkeypatch.setattr(backend_main, "load_runtime_environment_variables", lambda: {})
    monkeypatch.setattr(backend_main, "create_app", lambda runtime_config: fake_app)
    monkeypatch.setattr(
        backend_main,
        "TELEGRAM_LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: log_entries.append(f"{message} {payload}"),
            },
        )(),
    )

    exit_code = backend_main.main(["telegram-bot", "--drop-pending-updates"])

    assert exit_code == 0
    assert calls == [True]
    assert any("telegram_bot_polling_startup" in entry for entry in log_entries)


def test_recognition_async_processor_skips_duplicate_delivery_after_conflict(monkeypatch):
    refresh_calls: list[str] = []

    monkeypatch.setattr(
        recognition_async_jobs,
        "refresh_validations_for_material",
        lambda material_id, **_: refresh_calls.append(material_id),
    )

    now = datetime.now(timezone.utc)
    task = RecognitionTaskRecord(
        id="recognition-1",
        material_id="material-1",
        status=RecognitionTaskStatus.PENDING,
        created_at=now,
        updated_at=now,
    )

    class FakeRecognitionTaskRepository:
        def list_pending(self, *, limit: int):
            assert limit == 10
            return [task, task]

    class FakeRecognitionPreparationService:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def execute(self, recognition_task_id: str) -> RecognitionTaskRecord:
            self.calls.append(recognition_task_id)
            if len(self.calls) > 1:
                raise RecognitionTaskExecutionConflictError(
                    recognition_task_id,
                    RecognitionTaskStatus.SUCCEEDED,
                )
            return task.model_copy(update={"status": RecognitionTaskStatus.SUCCEEDED})

    preparation_service = FakeRecognitionPreparationService()
    metrics_collector = InMemoryMetricsCollector()
    processor = RecognitionAsyncJobProcessor(
        task_repository=object(),
        material_repository=object(),
        invoice_repository=object(),
        validation_repository=object(),
        recognition_task_repository=FakeRecognitionTaskRepository(),
        split_repository=object(),
        confirmation_repository=object(),
        recognition_preparation_service=preparation_service,
        metrics_collector=metrics_collector,
    )

    processed_count = processor.run_once()

    assert processed_count == 1
    assert preparation_service.calls == ["recognition-1", "recognition-1"]
    assert refresh_calls == ["material-1"]
    assert metrics_collector.snapshot()["validation_results"] == {
        "failed_rule_counts": {},
        "pending_rule_counts": {},
    }


def test_recognition_preparation_service_raise_missing_or_conflict_uses_repository_state():
    now = datetime.now(timezone.utc)

    class FakeRecognitionTaskRepository:
        def get(self, recognition_task_id: str):
            return RecognitionTaskRecord(
                id=recognition_task_id,
                material_id="material-1",
                status=RecognitionTaskStatus.SUCCEEDED,
                created_at=now,
                updated_at=now,
            )

    service = RecognitionPreparationService(
        material_repository=object(),
        material_file_storage=object(),
        recognition_task_repository=FakeRecognitionTaskRepository(),
        audit_log_repository=object(),
        llm_capability=object(),
        recognition_llm_client=None,
    )

    try:
        service._raise_missing_or_conflict("recognition-1")
    except RecognitionTaskExecutionConflictError as error:
        assert error.recognition_task_id == "recognition-1"
        assert error.status is RecognitionTaskStatus.SUCCEEDED
    else:  # pragma: no cover
        raise AssertionError("expected conflict error from repository state")


def test_recognition_async_processor_uses_worker_threads_for_batch_uploads(monkeypatch):
    monkeypatch.setattr(
        recognition_async_jobs,
        "refresh_validations_for_material",
        lambda material_id, **_: None,
    )

    now = datetime.now(timezone.utc)
    tasks = [
        RecognitionTaskRecord(
            id=f"recognition-{index}",
            material_id=f"material-{index}",
            status=RecognitionTaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        for index in range(3)
    ]
    active_lock = Lock()
    concurrent_execution_observed = Event()
    release = Event()
    active_count = 0
    max_active_count = 0

    class FakeRecognitionTaskRepository:
        def list_pending(self, *, limit: int):
            assert limit == 10
            return tasks

    class FakeRecognitionPreparationService:
        def execute(self, recognition_task_id: str) -> RecognitionTaskRecord:
            nonlocal active_count, max_active_count
            with active_lock:
                active_count += 1
                max_active_count = max(max_active_count, active_count)
                if active_count >= 2:
                    concurrent_execution_observed.set()
            release.wait(timeout=1)
            with active_lock:
                active_count -= 1
            task = next(item for item in tasks if item.id == recognition_task_id)
            return task.model_copy(update={"status": RecognitionTaskStatus.FAILED})

    processor = RecognitionAsyncJobProcessor(
        task_repository=object(),
        material_repository=object(),
        invoice_repository=object(),
        validation_repository=object(),
        recognition_task_repository=FakeRecognitionTaskRepository(),
        split_repository=object(),
        confirmation_repository=object(),
        recognition_preparation_service=FakeRecognitionPreparationService(),
        max_workers=2,
        metrics_collector=InMemoryMetricsCollector(),
    )

    worker_done = Event()
    processed_counts: list[int] = []

    def run_processor() -> None:
        processed_counts.append(processor.run_once())
        worker_done.set()

    thread = Thread(target=run_processor)
    thread.start()
    assert concurrent_execution_observed.wait(timeout=1)
    release.set()
    assert worker_done.wait(timeout=1)
    thread.join(timeout=1)

    assert processed_counts == [3]
    assert max_active_count >= 2


def test_recognition_async_processor_logs_processed_and_skipped_jobs(monkeypatch):
    refresh_calls: list[str] = []

    monkeypatch.setattr(
        recognition_async_jobs,
        "refresh_validations_for_material",
        lambda material_id, **_: refresh_calls.append(material_id),
    )

    now = datetime.now(timezone.utc)
    first_task = RecognitionTaskRecord(
        id="recognition-1",
        material_id="material-1",
        status=RecognitionTaskStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    second_task = first_task.model_copy(update={"id": "recognition-2", "material_id": "material-2"})

    class FakeRecognitionTaskRepository:
        def list_pending(self, *, limit: int):
            assert limit == 10
            return [first_task, second_task]

    class FakeRecognitionPreparationService:
        def execute(self, recognition_task_id: str) -> RecognitionTaskRecord:
            if recognition_task_id == "recognition-2":
                raise RecognitionTaskExecutionConflictError(
                    recognition_task_id,
                    RecognitionTaskStatus.SUCCEEDED,
                )
            return first_task.model_copy(update={"status": RecognitionTaskStatus.FAILED})

    entries: list[str] = []
    monkeypatch.setattr(
        recognition_async_jobs,
        "LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: entries.append(f"{message} {payload}"),
                "warning": lambda self, message, payload: entries.append(f"{message} {payload}"),
            },
        )(),
    )
    processor = RecognitionAsyncJobProcessor(
        task_repository=object(),
        material_repository=object(),
        invoice_repository=object(),
        validation_repository=object(),
        recognition_task_repository=FakeRecognitionTaskRepository(),
        split_repository=object(),
        confirmation_repository=object(),
        recognition_preparation_service=FakeRecognitionPreparationService(),
        metrics_collector=InMemoryMetricsCollector(),
    )

    assert processor.run_once() == 1
    assert refresh_calls == ["material-1"]
    assert any("recognition_worker_job_processed" in entry for entry in entries)
    assert any("recognition_worker_job_skipped" in entry for entry in entries)
    assert any("recognition-1" in entry for entry in entries)
    assert any("material-1" in entry for entry in entries)
    assert any("recognition-2" in entry for entry in entries)


def test_export_async_processor_skips_duplicate_delivery_after_claim(monkeypatch):
    now = datetime.now(timezone.utc)
    job = TaskExportJobRecord(
        id="export-1",
        task_id="task-1",
        requested_by="admin-1",
        kind="reimbursement_summary",
        format="csv",
        status=TaskExportJobStatus.PENDING,
        parameters={},
        task_data_version="a" * 64,
        created_at=now,
        updated_at=now,
    )
    job_statuses = {job.id: TaskExportJobStatus.PENDING}
    built_artifacts: list[StoredExportArtifactRecord] = []

    class FakeExportJobRepository:
        def list_pending(self, *, limit: int):
            assert limit == 10
            return [job, job]

        def update_status(
            self,
            export_job_id: str,
            *,
            target_status: TaskExportJobStatus,
            failure_reason: str | None = None,
            artifact: StoredExportArtifactRecord | None = None,
            expected_current_status: TaskExportJobStatus | None = None,
        ):
            current = job_statuses.get(export_job_id)
            if current is None:
                return None
            if expected_current_status is not None and current is not expected_current_status:
                return None
            job_statuses[export_job_id] = target_status
            if artifact is not None:
                built_artifacts.append(artifact)
            return job.model_copy(
                update={
                    "status": target_status,
                    "failure_reason": failure_reason,
                    "artifact": artifact,
                }
            )

    metrics_collector = InMemoryMetricsCollector()
    processor = ExportAsyncJobProcessor(
        task_repository=type("TaskRepo", (), {"get": lambda self, task_id: object()})(),
        export_job_repository=FakeExportJobRepository(),
        invoice_repository=object(),
        material_repository=object(),
        material_file_storage=object(),
        validation_repository=object(),
        split_repository=object(),
        confirmation_repository=object(),
        audit_log_repository=InMemoryAuditLogRepository(),
        metrics_collector=metrics_collector,
    )
    monkeypatch.setattr(
        processor,
        "_build_current_export_snapshot",
        lambda task: TaskExportVersionSnapshot(
            task_status="ready_to_export",
            task_data_version="a" * 64,
        ),
    )
    monkeypatch.setattr(
        processor,
        "_build_export_artifact",
        lambda task, export_job: StoredExportArtifactRecord(
            storage_key="task-1/_exports/file.csv",
            filename="file.csv",
            content_type="text/csv",
            size_bytes=12,
            sha256="b" * 64,
        ),
    )

    processed_count = processor.run_once()

    assert processed_count == 1
    assert job_statuses == {"export-1": TaskExportJobStatus.SUCCEEDED}
    assert len(built_artifacts) == 1
    assert metrics_collector.snapshot()["export_jobs"]["by_status"] == {
        "running": 1,
        "succeeded": 1,
    }


def test_export_async_processor_logs_failure_reason(monkeypatch):
    now = datetime.now(timezone.utc)
    job = TaskExportJobRecord(
        id="export-1",
        task_id="task-1",
        requested_by="admin-1",
        kind="reimbursement_summary",
        format="csv",
        status=TaskExportJobStatus.PENDING,
        parameters={},
        task_data_version="a" * 64,
        created_at=now,
        updated_at=now,
    )

    class FakeExportJobRepository:
        def list_pending(self, *, limit: int):
            assert limit == 10
            return [job]

        def update_status(
            self,
            export_job_id: str,
            *,
            target_status: TaskExportJobStatus,
            failure_reason: str | None = None,
            artifact: StoredExportArtifactRecord | None = None,
            expected_current_status: TaskExportJobStatus | None = None,
        ):
            return job.model_copy(
                update={
                    "status": target_status,
                    "failure_reason": failure_reason,
                    "artifact": artifact,
                }
            )

    entries: list[str] = []
    monkeypatch.setattr(
        "trms_backend.application.export_async_jobs.LOGGER",
        type(
            "Logger",
            (),
            {
                "info": lambda self, message, payload: entries.append(f"{message} {payload}"),
                "warning": lambda self, message, payload: entries.append(f"{message} {payload}"),
            },
        )(),
    )
    processor = ExportAsyncJobProcessor(
        task_repository=type("TaskRepo", (), {"get": lambda self, task_id: None})(),
        export_job_repository=FakeExportJobRepository(),
        invoice_repository=object(),
        material_repository=object(),
        material_file_storage=object(),
        validation_repository=object(),
        split_repository=object(),
        confirmation_repository=object(),
        audit_log_repository=InMemoryAuditLogRepository(),
        metrics_collector=InMemoryMetricsCollector(),
    )

    assert processor.run_once() == 1
    assert any("export_worker_job_failed" in entry for entry in entries)
    assert any("export-1" in entry for entry in entries)
    assert any("task not found" in entry for entry in entries)
