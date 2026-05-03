from __future__ import annotations

from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
import imaplib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from trms_backend.application.async_jobs import AsyncJobProcessor
from trms_backend.application.email_material_submission import EmailMaterialSubmissionService
from trms_backend.application.email_material_submission import (
    EmailMaterialSubmissionFormatError,
    ParsedEmailSubmission,
    extract_email_attachments,
    extract_email_body,
    parse_formatted_email_submission,
)
from trms_backend.application.material_submission import MaterialSubmissionTaskNotOpenError
from trms_backend.application.outbound_email import OutboundEmailMessage, OutboundEmailSender
from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
from trms_backend.domain.email_bindings import (
    EmailSubmissionIdentityResolver,
    EmailSubmissionIdentityStatus,
)
from trms_backend.domain.email_inbox import (
    EmailInboxRecordCreate,
    EmailInboxRecordRepository,
    EmailInboxRecordStatus,
)
from trms_backend.domain.tasks import TaskRepository
from trms_backend.domain.tasks import TaskSubmissionDeadlinePassedError, TaskSubmitterNotMemberError
from trms_backend.domain.materials import MaterialFileStorage
from trms_backend.runtime_config import EmailInboxConfig
from trms_backend.logging_safety import sanitize_log_fields

LOGGER = logging.getLogger("trms_backend.worker")
SYSTEM_EMAIL_POLL_ACTOR_ID = "system:email-inbox-worker"


@dataclass(frozen=True)
class PolledEmailMessage:
    mailbox_uid: str
    message_id: str | None
    sender_email: str
    subject: str
    body: str
    raw_bytes: bytes
    received_at: datetime | None


class EmailInboxClient(Protocol):
    def fetch_new_messages(self, *, after_uid: str | None = None) -> list[PolledEmailMessage]:
        raise NotImplementedError


class EmailInboxPollingProcessor(AsyncJobProcessor):
    job_type = "email_inbox"

    def __init__(
        self,
        *,
        email_inbox_client: EmailInboxClient,
        email_inbox_record_repository: EmailInboxRecordRepository,
        email_submission_identity_resolver: EmailSubmissionIdentityResolver,
        task_repository: TaskRepository,
        raw_email_storage: MaterialFileStorage,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._email_inbox_client = email_inbox_client
        self._email_inbox_record_repository = email_inbox_record_repository
        self._email_submission_identity_resolver = email_submission_identity_resolver
        self._task_repository = task_repository
        self._raw_email_storage = raw_email_storage
        self._audit_log_repository = audit_log_repository

    def run_once(self) -> int:
        processed_count = 0
        last_seen_uid = self._email_inbox_record_repository.get_max_mailbox_uid()
        for message in self._email_inbox_client.fetch_new_messages(after_uid=last_seen_uid):
            if self._email_inbox_record_repository.get_by_mailbox_uid(message.mailbox_uid) is not None:
                continue
            self._ingest_message(message)
            processed_count += 1
        return processed_count

    def _ingest_message(self, message: PolledEmailMessage) -> None:
        try:
            resolved_identity = self._email_submission_identity_resolver.resolve(message.sender_email)
        except ValueError:
            self._record_ignored_message(
                message=message,
                result_code="ignored_invalid_sender_email",
                resolved_member_id=None,
                submitted_task_key=None,
                resolved_task_id=None,
            )
            return
        parsed_email: ParsedEmailSubmission | None = None
        result_code: str
        status: EmailInboxRecordStatus
        resolved_task_id: str | None = None
        submitted_task_key: str | None = None

        if resolved_identity.status is not EmailSubmissionIdentityStatus.BOUND:
            result_code = "ignored_unbound_sender"
            status = EmailInboxRecordStatus.IGNORED
        else:
            try:
                parsed_email = parse_formatted_email_submission(
                    sender_email=message.sender_email,
                    subject=message.subject,
                    body=message.body,
                    task_repository=self._task_repository,
                )
            except EmailMaterialSubmissionFormatError as error:
                result_code = error.error_code
                status = EmailInboxRecordStatus.IGNORED
            else:
                submitted_task_key = parsed_email.submitted_task_key
                resolved_task = self._task_repository.get(parsed_email.task_id)
                if resolved_task is None:
                    result_code = "ignored_unknown_task_key"
                    status = EmailInboxRecordStatus.IGNORED
                else:
                    result_code = "ready_for_import"
                    status = EmailInboxRecordStatus.READY_FOR_IMPORT
                    resolved_task_id = resolved_task.id

        self._record_ignored_or_ready_message(
            message=message,
            status=status,
            result_code=result_code,
            resolved_member_id=resolved_identity.member_id,
            submitted_task_key=submitted_task_key,
            resolved_task_id=resolved_task_id,
        )

    def _record_ignored_message(
        self,
        *,
        message: PolledEmailMessage,
        result_code: str,
        resolved_member_id: str | None,
        submitted_task_key: str | None,
        resolved_task_id: str | None,
    ) -> None:
        self._record_ignored_or_ready_message(
            message=message,
            status=EmailInboxRecordStatus.IGNORED,
            result_code=result_code,
            resolved_member_id=resolved_member_id,
            submitted_task_key=submitted_task_key,
            resolved_task_id=resolved_task_id,
        )

    def _record_ignored_or_ready_message(
        self,
        *,
        message: PolledEmailMessage,
        status: EmailInboxRecordStatus,
        result_code: str,
        resolved_member_id: str | None,
        submitted_task_key: str | None,
        resolved_task_id: str | None,
    ) -> None:
        stored_raw_email = self._raw_email_storage.save(
            task_id="_email_inbox",
            original_filename=f"{message.mailbox_uid}.eml",
            content_type="message/rfc822",
            content=message.raw_bytes,
        )
        record = self._email_inbox_record_repository.create(
            EmailInboxRecordCreate(
                mailbox_uid=message.mailbox_uid,
                message_id=message.message_id,
                sender_email=message.sender_email,
                subject=message.subject,
                raw_storage_key=stored_raw_email.storage_key,
                received_at=message.received_at,
                status=status,
                result_code=result_code,
                resolved_member_id=resolved_member_id,
                submitted_task_key=submitted_task_key,
                resolved_task_id=resolved_task_id,
            )
        )
        self._audit_log_repository.create(
            AuditLogCreate(
                actor_id=SYSTEM_EMAIL_POLL_ACTOR_ID,
                object_type="email_inbox_record",
                object_id=record.id,
                action="poll_email_inbox_message",
                result=AuditLogResult.SUCCEEDED,
                summary=f"polled email inbox message {record.mailbox_uid}",
                detail={
                    "mailbox_uid": record.mailbox_uid,
                    "message_id": record.message_id,
                    "sender_email": record.sender_email,
                    "status": record.status,
                    "result_code": record.result_code,
                    "submitted_task_key": record.submitted_task_key,
                    "resolved_task_id": record.resolved_task_id,
                },
                task_id=record.resolved_task_id,
                request_id=None,
            )
        )
        LOGGER.info(
            "email_inbox_message_polled %s",
            sanitize_log_fields(
                {
                    "mailbox_uid": record.mailbox_uid,
                    "message_id": record.message_id,
                    "sender_email": record.sender_email,
                    "status": record.status,
                    "result_code": record.result_code,
                    "resolved_member_id": record.resolved_member_id,
                    "resolved_task_id": record.resolved_task_id,
                }
            ),
        )


class EmailInboxImportProcessor(AsyncJobProcessor):
    job_type = "email_inbox_import"

    def __init__(
        self,
        *,
        email_inbox_record_repository: EmailInboxRecordRepository,
        raw_email_storage: MaterialFileStorage,
        email_material_submission_service: EmailMaterialSubmissionService,
        outbound_email_sender: OutboundEmailSender | None,
        audit_log_repository: AuditLogRepository,
        batch_size: int = 10,
    ) -> None:
        self._email_inbox_record_repository = email_inbox_record_repository
        self._raw_email_storage = raw_email_storage
        self._email_material_submission_service = email_material_submission_service
        self._outbound_email_sender = outbound_email_sender
        self._audit_log_repository = audit_log_repository
        self._batch_size = batch_size

    def run_once(self) -> int:
        processed_count = 0
        for record in self._email_inbox_record_repository.list_ready_for_import(limit=self._batch_size):
            self._import_record(record.id)
            processed_count += 1
        return processed_count

    def _import_record(self, record_id: str) -> None:
        record = self._email_inbox_record_repository.get(record_id)
        if record is None or record.status is not EmailInboxRecordStatus.READY_FOR_IMPORT:
            return
        raw_email = self._raw_email_storage.read(storage_key=record.raw_storage_key)
        parsed = BytesParser(policy=policy.default).parsebytes(raw_email)
        body = extract_email_body(parsed)
        attachments = extract_email_attachments(parsed)
        if not attachments:
            updated = self._email_inbox_record_repository.update_result(
                record.id,
                status=EmailInboxRecordStatus.IMPORT_FAILED,
                result_code="missing_attachments",
            )
            if updated is not None:
                self._send_result_email(updated, success_count=0, failure_count=0)
            return

        try:
            result = self._email_material_submission_service.submit(
                sender_email=record.sender_email,
                subject=record.subject,
                body=body,
                resolved_member_id=record.resolved_member_id,
                files=attachments,
                request_id=None,
            )
        except EmailMaterialSubmissionFormatError:
            updated = self._email_inbox_record_repository.update_result(
                record.id,
                status=EmailInboxRecordStatus.IMPORT_FAILED,
                result_code="import_format_error",
            )
            if updated is not None:
                self._send_result_email(updated, success_count=0, failure_count=0)
            return
        except MaterialSubmissionTaskNotOpenError:
            updated = self._email_inbox_record_repository.update_result(
                record.id,
                status=EmailInboxRecordStatus.IMPORT_FAILED,
                result_code="import_task_not_open",
            )
            if updated is not None:
                self._send_result_email(updated, success_count=0, failure_count=0)
            return
        except TaskSubmitterNotMemberError:
            updated = self._email_inbox_record_repository.update_result(
                record.id,
                status=EmailInboxRecordStatus.IMPORT_FAILED,
                result_code="import_submitter_not_member",
            )
            if updated is not None:
                self._send_result_email(updated, success_count=0, failure_count=0)
            return
        except TaskSubmissionDeadlinePassedError:
            updated = self._email_inbox_record_repository.update_result(
                record.id,
                status=EmailInboxRecordStatus.IMPORT_FAILED,
                result_code="import_deadline_passed",
            )
            if updated is not None:
                self._send_result_email(updated, success_count=0, failure_count=0)
            return
        success_count = len(result.material_submission.records)
        failure_count = len(result.material_submission.failures)
        if success_count > 0 and failure_count == 0:
            updated_status = EmailInboxRecordStatus.IMPORTED
            result_code = "imported"
        elif success_count > 0:
            updated_status = EmailInboxRecordStatus.PARTIALLY_IMPORTED
            result_code = "partially_imported"
        else:
            updated_status = EmailInboxRecordStatus.IMPORT_FAILED
            result_code = "import_failed"
        updated = self._email_inbox_record_repository.update_result(
            record.id,
            status=updated_status,
            result_code=result_code,
        )
        if updated is not None:
            self._audit_log_repository.create(
                AuditLogCreate(
                    actor_id=SYSTEM_EMAIL_POLL_ACTOR_ID,
                    object_type="email_inbox_record",
                    object_id=updated.id,
                    action="import_email_inbox_message",
                    result=AuditLogResult.SUCCEEDED,
                    summary=f"import email inbox message {updated.mailbox_uid}",
                    detail={
                        "status": updated.status,
                        "result_code": updated.result_code,
                        "success_count": success_count,
                        "failure_count": failure_count,
                    },
                    task_id=updated.resolved_task_id,
                    request_id=None,
                )
            )
            self._send_result_email(updated, success_count=success_count, failure_count=failure_count)

    def _send_result_email(
        self,
        record,
        *,
        success_count: int,
        failure_count: int,
    ) -> None:
        if self._outbound_email_sender is None:
            return
        if record.status is EmailInboxRecordStatus.IMPORTED:
            subject = "TRMS 邮件材料已收到"
            body = f"你的邮件材料已收到并进入任务处理链路。\n成功附件数：{success_count}\n"
        elif record.status is EmailInboxRecordStatus.PARTIALLY_IMPORTED:
            subject = "TRMS 邮件材料部分成功"
            body = (
                "你的邮件材料已部分进入任务处理链路。\n"
                f"成功附件数：{success_count}\n失败附件数：{failure_count}\n"
            )
        else:
            subject = "TRMS 邮件材料处理失败"
            body = f"你的邮件材料未成功进入任务处理链路。\n失败原因：{record.result_code}\n"
        self._outbound_email_sender.send(
            OutboundEmailMessage(
                to_email=record.sender_email,
                subject=subject,
                text_body=body,
            )
        )


class StaticEmailInboxClient:
    def __init__(self, messages: list[PolledEmailMessage]) -> None:
        self._messages = messages

    def fetch_new_messages(self, *, after_uid: str | None = None) -> list[PolledEmailMessage]:
        if after_uid is None:
            return list(self._messages)
        return [
            message
            for message in self._messages
            if _mailbox_uid_is_after(message.mailbox_uid, after_uid)
        ]


class ImapEmailInboxClient:
    def __init__(self, config: EmailInboxConfig) -> None:
        self._config = config

    def fetch_new_messages(self, *, after_uid: str | None = None) -> list[PolledEmailMessage]:
        if self._config.use_ssl:
            connection = imaplib.IMAP4_SSL(self._config.host, self._config.port)
        else:
            connection = imaplib.IMAP4(self._config.host, self._config.port)
        try:
            if self._config.starttls:
                connection.starttls()
            connection.login(self._config.username, self._config.password.get_secret_value())
            connection.select(self._config.mailbox)
            search_criteria = "ALL" if after_uid is None else f"UID {after_uid}:*"
            status, data = connection.uid("search", None, search_criteria)
            if status != "OK":
                return []
            messages: list[PolledEmailMessage] = []
            for raw_uid in data[0].split():
                uid = raw_uid.decode("utf-8")
                if after_uid is not None and not _mailbox_uid_is_after(uid, after_uid):
                    continue
                fetch_status, fetch_data = connection.uid("fetch", raw_uid, "(RFC822)")
                if fetch_status != "OK" or not fetch_data:
                    continue
                raw_email = _extract_raw_email_bytes(fetch_data)
                if raw_email is None:
                    continue
                parsed = BytesParser(policy=policy.default).parsebytes(raw_email)
                sender_email = parsed.get("From", "")
                subject = parsed.get("Subject", "")
                body = extract_email_body(parsed)
                messages.append(
                    PolledEmailMessage(
                        mailbox_uid=uid,
                        message_id=parsed.get("Message-ID"),
                        sender_email=_extract_email_address(sender_email),
                        subject=subject,
                        body=body,
                        raw_bytes=raw_email,
                        received_at=_extract_received_at(parsed.get("Date")),
                    )
                )
            return messages
        finally:
            try:
                connection.logout()
            except Exception:  # pragma: no cover - best effort cleanup
                pass


def _extract_raw_email_bytes(fetch_data) -> bytes | None:
    for item in fetch_data:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    return None


def _extract_email_address(raw_from: str) -> str:
    if "<" in raw_from and ">" in raw_from:
        return raw_from.rsplit("<", maxsplit=1)[-1].split(">", maxsplit=1)[0].strip()
    return raw_from.strip()


def _extract_received_at(raw_date: str | None) -> datetime | None:
    if raw_date is None:
        return None
    try:
        parsed = parsedate_to_datetime(raw_date)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _mailbox_uid_is_after(candidate: str, baseline: str) -> bool:
    if candidate.isdigit() and baseline.isdigit():
        return int(candidate) > int(baseline)
    return candidate > baseline
