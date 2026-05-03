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
from trms_backend.application.email_material_submission import (
    EmailMaterialSubmissionFormatError,
    ParsedEmailSubmission,
    parse_formatted_email_submission,
)
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
    def fetch_new_messages(self) -> list[PolledEmailMessage]:
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
        for message in self._email_inbox_client.fetch_new_messages():
            if self._email_inbox_record_repository.get_by_mailbox_uid(message.mailbox_uid) is not None:
                continue
            self._ingest_message(message)
            processed_count += 1
        return processed_count

    def _ingest_message(self, message: PolledEmailMessage) -> None:
        resolved_identity = self._email_submission_identity_resolver.resolve(message.sender_email)
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
                resolved_member_id=resolved_identity.member_id,
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


class StaticEmailInboxClient:
    def __init__(self, messages: list[PolledEmailMessage]) -> None:
        self._messages = messages

    def fetch_new_messages(self) -> list[PolledEmailMessage]:
        return list(self._messages)


class ImapEmailInboxClient:
    def __init__(self, config: EmailInboxConfig) -> None:
        self._config = config

    def fetch_new_messages(self) -> list[PolledEmailMessage]:
        if self._config.use_ssl:
            connection = imaplib.IMAP4_SSL(self._config.host, self._config.port)
        else:
            connection = imaplib.IMAP4(self._config.host, self._config.port)
        try:
            if self._config.starttls:
                connection.starttls()
            connection.login(self._config.username, self._config.password.get_secret_value())
            connection.select(self._config.mailbox)
            status, data = connection.uid("search", None, "ALL")
            if status != "OK":
                return []
            messages: list[PolledEmailMessage] = []
            for raw_uid in data[0].split():
                uid = raw_uid.decode("utf-8")
                fetch_status, fetch_data = connection.uid("fetch", raw_uid, "(RFC822)")
                if fetch_status != "OK" or not fetch_data:
                    continue
                raw_email = _extract_raw_email_bytes(fetch_data)
                if raw_email is None:
                    continue
                parsed = BytesParser(policy=policy.default).parsebytes(raw_email)
                sender_email = parsed.get("From", "")
                subject = parsed.get("Subject", "")
                body = _extract_email_body(parsed)
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


def _extract_email_body(message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_maintype() != "text":
                continue
            if part.get_content_subtype() != "plain":
                continue
            content_disposition = part.get_content_disposition()
            if content_disposition == "attachment":
                continue
            try:
                return part.get_content()
            except Exception:
                continue
        return ""
    try:
        return message.get_content()
    except Exception:
        return ""


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
