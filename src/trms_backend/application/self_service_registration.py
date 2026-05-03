from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from trms_backend.application.outbound_email import OutboundEmailMessage, OutboundEmailSender
from trms_backend.domain.auth import (
    ACCESS_TOKEN_BYTES,
    AuthSession,
    AuthenticatedUser,
    UserRegisterInput,
    UsernameAlreadyExistsError,
    hash_token,
    prepare_self_service_user_create,
)
from trms_backend.domain.email_bindings import (
    EmailAccountBindingConflictError,
    normalize_email_address,
)
from trms_backend.domain.registration_policy import RegistrationPolicy, RegistrationPolicyRepository
from trms_backend.infrastructure.database import session_scope
from trms_backend.infrastructure.models import (
    AuthSessionRow,
    EmailAccountBindingRow,
    RegistrationEmailVerificationRow,
    UserAccountRow,
)


REGISTRATION_EMAIL_VERIFICATION_TTL = timedelta(minutes=10)


class OutboundEmailNotConfiguredError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("outbound email is not configured")


class RegistrationEmailRequiredError(ValueError):
    def __init__(self) -> None:
        super().__init__("registration email is required in production")


class RegistrationEmailVerificationCodeRequiredError(ValueError):
    def __init__(self) -> None:
        super().__init__("registration email verification code is required in production")


class RegistrationEmailVerificationCodeInvalidError(ValueError):
    def __init__(self) -> None:
        super().__init__("registration email verification code is invalid")


class RegistrationEmailVerificationCodeExpiredError(ValueError):
    def __init__(self) -> None:
        super().__init__("registration email verification code has expired")


class RegistrationEmailHostNotAllowedError(ValueError):
    def __init__(self, host: str) -> None:
        super().__init__(f"self-service registration is not allowed for email host '{host}'")


@dataclass(frozen=True)
class RegistrationEmailVerificationDispatchResult:
    email: str
    expires_at: datetime


class SelfServiceRegistrationService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        registration_policy_repository: RegistrationPolicyRepository,
        outbound_email_sender: OutboundEmailSender | None,
        *,
        environment: str,
        allow_privileged_self_registration: bool,
    ) -> None:
        self._session_factory = session_factory
        self._registration_policy_repository = registration_policy_repository
        self._outbound_email_sender = outbound_email_sender
        self._environment = environment
        self._allow_privileged_self_registration = allow_privileged_self_registration

    def send_verification_code(self, *, email: str) -> RegistrationEmailVerificationDispatchResult:
        if self._outbound_email_sender is None:
            raise OutboundEmailNotConfiguredError()

        normalized_email = normalize_email_address(email)
        if self._environment == "production":
            self._ensure_email_host_allowed(normalized_email)

        now = datetime.now(UTC)
        verification_code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = now + REGISTRATION_EMAIL_VERIFICATION_TTL
        code_hash = _hash_verification_code(normalized_email, verification_code)

        with session_scope(self._session_factory) as session:
            existing_binding = session.scalar(
                select(EmailAccountBindingRow)
                .where(EmailAccountBindingRow.email == normalized_email)
                .limit(1)
            )
            if existing_binding is not None:
                raise EmailAccountBindingConflictError(
                    "email is already bound to another member: "
                    f"{normalized_email}"
                )

            existing_rows = session.scalars(
                select(RegistrationEmailVerificationRow).where(
                    RegistrationEmailVerificationRow.email == normalized_email,
                    RegistrationEmailVerificationRow.consumed_at.is_(None),
                )
            ).all()
            for existing_row in existing_rows:
                existing_row.consumed_at = now
                session.add(existing_row)

            session.add(
                RegistrationEmailVerificationRow(
                    id=str(uuid4()),
                    email=normalized_email,
                    code_hash=code_hash,
                    expires_at=expires_at,
                    consumed_at=None,
                    created_at=now,
                )
            )

        self._outbound_email_sender.send(
            OutboundEmailMessage(
                to_email=normalized_email,
                subject="TRMS 注册验证码",
                text_body=(
                    "你正在注册 TRMS 账号。\n\n"
                    f"验证码：{verification_code}\n"
                    "有效期：10 分钟\n\n"
                    "如果这不是你的操作，请忽略这封邮件。"
                ),
            )
        )
        return RegistrationEmailVerificationDispatchResult(
            email=normalized_email,
            expires_at=expires_at,
        )

    def register(self, payload: UserRegisterInput) -> AuthSession:
        user_create = prepare_self_service_user_create(
            payload,
            allow_privileged_self_registration=self._allow_privileged_self_registration,
        )

        requires_email_verification = self._environment == "production"
        normalized_email = payload.email
        normalized_code = payload.email_verification_code

        if requires_email_verification and normalized_email is None:
            raise RegistrationEmailRequiredError()
        if requires_email_verification and normalized_code is None:
            raise RegistrationEmailVerificationCodeRequiredError()
        if (normalized_email is None) != (normalized_code is None):
            if normalized_email is None:
                raise RegistrationEmailRequiredError()
            raise RegistrationEmailVerificationCodeRequiredError()

        now = datetime.now(UTC)
        access_token = secrets.token_urlsafe(ACCESS_TOKEN_BYTES)
        with session_scope(self._session_factory) as session:
            if session.scalar(
                select(UserAccountRow)
                .where(UserAccountRow.username == user_create.username)
                .limit(1)
            ) is not None:
                raise UsernameAlreadyExistsError(user_create.username)

            verification_row: RegistrationEmailVerificationRow | None = None
            if normalized_email is not None and normalized_code is not None:
                normalized_email = normalize_email_address(normalized_email)
                if self._environment == "production":
                    self._ensure_email_host_allowed(normalized_email)
                verification_row = session.scalar(
                    select(RegistrationEmailVerificationRow)
                    .where(
                        RegistrationEmailVerificationRow.email == normalized_email,
                        RegistrationEmailVerificationRow.consumed_at.is_(None),
                    )
                    .order_by(RegistrationEmailVerificationRow.created_at.desc())
                    .limit(1)
                )
                if verification_row is None:
                    raise RegistrationEmailVerificationCodeInvalidError()
                if _coerce_utc_datetime(verification_row.expires_at) < now:
                    raise RegistrationEmailVerificationCodeExpiredError()
                expected_code_hash = _hash_verification_code(normalized_email, normalized_code)
                if not hmac.compare_digest(expected_code_hash, verification_row.code_hash):
                    raise RegistrationEmailVerificationCodeInvalidError()

                existing_binding = session.scalar(
                    select(EmailAccountBindingRow)
                    .where(EmailAccountBindingRow.email == normalized_email)
                    .limit(1)
                )
                if existing_binding is not None:
                    raise EmailAccountBindingConflictError(
                        "email is already bound to another member: "
                        f"{normalized_email}"
                    )

            user_row = UserAccountRow(
                id=str(uuid4()),
                username=user_create.username,
                password_hash=user_create.password_hash,
                role=user_create.role.value,
                roles=[role.value for role in user_create.roles],
                actor_id=user_create.actor_id,
                display_name=user_create.display_name,
                member_code=user_create.member_code,
                registration_source=user_create.registration_source.value,
                created_by_user_id=user_create.created_by_user_id,
                created_at=now,
                updated_at=now,
            )
            session.add(user_row)
            try:
                session.flush()
            except IntegrityError as error:
                raise UsernameAlreadyExistsError(user_create.username) from error

            if normalized_email is not None:
                session.add(
                    EmailAccountBindingRow(
                        id=str(uuid4()),
                        member_id=user_row.actor_id,
                        email=normalized_email,
                        created_at=now,
                        updated_at=now,
                    )
                )
            if verification_row is not None:
                verification_row.consumed_at = now
                session.add(verification_row)
            session.add(
                AuthSessionRow(
                    id=str(uuid4()),
                    user_id=user_row.id,
                    token_hash=hash_token(access_token),
                    active_role=user_row.role,
                    created_at=now,
                    revoked_at=None,
                )
            )

            try:
                session.flush()
            except IntegrityError as error:
                raise EmailAccountBindingConflictError(
                    "email is already bound to another member: "
                    f"{normalized_email}"
                ) from error

        return AuthSession(
            access_token=access_token,
            user=_authenticated_user_from_row(user_row),
        )

    def _ensure_email_host_allowed(self, email: str) -> None:
        policy = self._registration_policy_repository.get() or RegistrationPolicy()
        if policy.is_email_allowed(email):
            return
        host = email.rsplit("@", maxsplit=1)[-1]
        raise RegistrationEmailHostNotAllowedError(host)


def _hash_verification_code(email: str, code: str) -> str:
    normalized_code = code.strip()
    if len(normalized_code) != 6 or not normalized_code.isdigit():
        raise RegistrationEmailVerificationCodeInvalidError()
    return hashlib.sha256(f"{email}:{normalized_code}".encode("utf-8")).hexdigest()


def _coerce_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _authenticated_user_from_row(row: UserAccountRow) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=row.id,
        username=row.username,
        role=row.role,
        roles=list(row.roles),
        actor_id=row.actor_id,
        display_name=row.display_name,
        member_code=row.member_code,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
