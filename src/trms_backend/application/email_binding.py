from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Callable

from trms_backend.application.outbound_email import OutboundEmailMessage, OutboundEmailSender
from trms_backend.domain.email_bindings import (
    EmailAccountBindingConflictError,
    EmailAccountBindingRecord,
    EmailAccountBindingRepository,
    EmailAccountBindingUpsert,
    EmailBindingVerificationCreate,
    EmailBindingVerificationRepository,
    normalize_email_address,
)

EMAIL_BINDING_VERIFICATION_TTL = timedelta(minutes=10)


class OutboundEmailNotConfiguredError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("outbound email is not configured")


class EmailBindingVerificationCodeInvalidError(ValueError):
    def __init__(self) -> None:
        super().__init__("email verification code is invalid")


class EmailBindingVerificationCodeExpiredError(ValueError):
    def __init__(self) -> None:
        super().__init__("email verification code has expired")


@dataclass(frozen=True)
class EmailBindingVerificationDispatchResult:
    email: str
    expires_at: datetime


class EmailBindingService:
    def __init__(
        self,
        binding_repository: EmailAccountBindingRepository,
        verification_repository: EmailBindingVerificationRepository,
        outbound_email_sender: OutboundEmailSender | None,
        *,
        code_generator: Callable[[], str] | None = None,
    ) -> None:
        self._binding_repository = binding_repository
        self._verification_repository = verification_repository
        self._outbound_email_sender = outbound_email_sender
        self._code_generator = code_generator or _generate_verification_code

    def list_bindings(self, *, member_id: str) -> list[EmailAccountBindingRecord]:
        normalized_member_id = _normalize_member_id(member_id)
        return self._binding_repository.list_by_member_id(normalized_member_id)

    def send_verification_code(
        self,
        *,
        member_id: str,
        email: str,
    ) -> EmailBindingVerificationDispatchResult:
        if self._outbound_email_sender is None:
            raise OutboundEmailNotConfiguredError()

        normalized_member_id = _normalize_member_id(member_id)
        normalized_email = normalize_email_address(email)
        existing_binding = self._binding_repository.get_by_email(normalized_email)
        if existing_binding is not None and existing_binding.member_id != normalized_member_id:
            raise EmailAccountBindingConflictError(
                "email is already bound to another member: "
                f"{normalized_email}"
            )
        now = datetime.now(UTC)
        verification_code = self._code_generator()
        expires_at = now + EMAIL_BINDING_VERIFICATION_TTL

        self._verification_repository.replace_pending(
            EmailBindingVerificationCreate(
                member_id=normalized_member_id,
                email=normalized_email,
                code_hash=_hash_verification_code(normalized_email, verification_code),
                expires_at=expires_at,
            )
        )
        self._outbound_email_sender.send(
            OutboundEmailMessage(
                to_email=normalized_email,
                subject="TRMS 邮箱绑定验证码",
                text_body=(
                    "你正在绑定 TRMS 邮箱提交地址。\n\n"
                    f"验证码：{verification_code}\n"
                    "有效期：10 分钟\n\n"
                    "如果这不是你的操作，请忽略这封邮件。"
                ),
            )
        )
        return EmailBindingVerificationDispatchResult(
            email=normalized_email,
            expires_at=expires_at,
        )

    def verify_code(
        self,
        *,
        member_id: str,
        email: str,
        code: str,
    ) -> EmailAccountBindingRecord:
        normalized_member_id = _normalize_member_id(member_id)
        normalized_email = normalize_email_address(email)
        normalized_code = _normalize_verification_code(code)

        verification = self._verification_repository.get_latest_pending(
            member_id=normalized_member_id,
            email=normalized_email,
        )
        if verification is None:
            raise EmailBindingVerificationCodeInvalidError()

        now = datetime.now(UTC)
        if verification.expires_at < now:
            raise EmailBindingVerificationCodeExpiredError()

        expected_code_hash = _hash_verification_code(normalized_email, normalized_code)
        if not hmac.compare_digest(expected_code_hash, verification.code_hash):
            raise EmailBindingVerificationCodeInvalidError()

        self._verification_repository.mark_consumed(
            verification.id,
            consumed_at=now,
        )
        return self._binding_repository.upsert(
            EmailAccountBindingUpsert(
                member_id=normalized_member_id,
                email=normalized_email,
            )
        )


def _generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_verification_code(email: str, code: str) -> str:
    return hashlib.sha256(f"{email}:{code}".encode("utf-8")).hexdigest()


def _normalize_member_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("member_id must not be empty")
    return normalized


def _normalize_verification_code(value: str) -> str:
    normalized = value.strip()
    if len(normalized) != 6 or not normalized.isdigit():
        raise EmailBindingVerificationCodeInvalidError()
    return normalized
