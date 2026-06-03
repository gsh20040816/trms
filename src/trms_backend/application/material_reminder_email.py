from __future__ import annotations

from datetime import UTC, datetime

from trms_backend.application.outbound_email import OutboundEmailMessage, OutboundEmailSender
from trms_backend.domain.email_bindings import EmailAccountBindingRepository
from trms_backend.domain.material_reminders import (
    MaterialReminderCreate,
    MaterialReminderEmailDeliveryStatus,
    MaterialReminderRecord,
    MaterialReminderRepository,
    create_task_material_reminder,
)
from trms_backend.domain.tasks import ReimbursementTask


class MaterialReminderEmailDispatchService:
    def __init__(
        self,
        *,
        reminder_repository: MaterialReminderRepository,
        email_binding_repository: EmailAccountBindingRepository,
        outbound_email_sender: OutboundEmailSender | None,
    ) -> None:
        self._reminder_repository = reminder_repository
        self._email_binding_repository = email_binding_repository
        self._outbound_email_sender = outbound_email_sender

    def create_and_send(
        self,
        task: ReimbursementTask,
        *,
        administrator_id: str,
        member_ids: list[str],
        content: str,
        email_subject: str | None = None,
        email_body: str | None = None,
    ) -> list[MaterialReminderRecord]:
        records: list[MaterialReminderRecord] = []
        normalized_subject = _normalize_optional_text(email_subject)
        normalized_body = _normalize_optional_text(email_body)

        for member_id in member_ids:
            primary_email = self._resolve_primary_email(member_id)
            subject = normalized_subject or build_default_reminder_email_subject(task)
            body = normalized_body or build_default_reminder_email_body(
                task,
                member_id=member_id,
                content=content,
            )
            reminder = create_task_material_reminder(
                task,
                reminder_repository=self._reminder_repository,
                payload=MaterialReminderCreate(
                    administrator_id=administrator_id,
                    member_id=member_id,
                    content=content,
                    email_recipient=primary_email,
                    email_subject=subject,
                    email_body=body,
                    email_delivery_status=MaterialReminderEmailDeliveryStatus.PENDING,
                ),
            )
            records.append(self._send_and_update(reminder))

        return records

    def _resolve_primary_email(self, member_id: str) -> str | None:
        bindings = self._email_binding_repository.list_by_member_id(member_id)
        if not bindings:
            return None
        return bindings[0].email

    def _send_and_update(self, reminder: MaterialReminderRecord) -> MaterialReminderRecord:
        if reminder.email_recipient is None:
            return self._update_failed(
                reminder,
                reason="member has no primary email binding",
            )
        if self._outbound_email_sender is None:
            return self._update_failed(
                reminder,
                reason="outbound email is not configured",
            )
        if reminder.email_subject is None or reminder.email_body is None:
            return self._update_failed(
                reminder,
                reason="email subject and body are required",
            )

        try:
            self._outbound_email_sender.send(
                OutboundEmailMessage(
                    to_email=reminder.email_recipient,
                    subject=reminder.email_subject,
                    text_body=reminder.email_body,
                )
            )
        except Exception as error:  # pragma: no cover - exercised through injected test sender
            return self._update_failed(
                reminder,
                reason=_truncate_failure_reason(str(error) or error.__class__.__name__),
            )

        updated = self._reminder_repository.update_email_delivery(
            reminder.id,
            status=MaterialReminderEmailDeliveryStatus.SENT,
            sent_at=datetime.now(UTC),
            failure_reason=None,
        )
        return updated or reminder

    def _update_failed(
        self,
        reminder: MaterialReminderRecord,
        *,
        reason: str,
    ) -> MaterialReminderRecord:
        updated = self._reminder_repository.update_email_delivery(
            reminder.id,
            status=MaterialReminderEmailDeliveryStatus.FAILED,
            sent_at=None,
            failure_reason=_truncate_failure_reason(reason),
        )
        return updated or reminder


def build_default_reminder_email_subject(task: ReimbursementTask) -> str:
    return _truncate_text(f"TRMS 报销任务提醒：{task.competition_name}", 255)


def build_default_reminder_email_body(
    task: ReimbursementTask,
    *,
    member_id: str,
    content: str,
) -> str:
    return (
        "这是一封 TRMS 自动化提醒邮件，无需直接回复本邮件。\n\n"
        f"任务：{task.competition_name}\n"
        f"任务编号：{task.id}\n"
        f"提醒对象：{member_id}\n\n"
        "提醒内容：\n"
        f"{content.strip()}\n\n"
        "请登录 TRMS 查看任务详情，并按提醒补充材料或确认费用。\n"
        "如果你已经完成相关操作，请忽略这封邮件。"
    )


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _truncate_failure_reason(value: str) -> str:
    return _truncate_text(value, 1000)


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "..."
