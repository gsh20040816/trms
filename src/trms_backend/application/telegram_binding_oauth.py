from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import secrets

from trms_backend.domain.telegram_bindings import (
    TelegramAccountBindingConflictError,
    TelegramAccountBindingRepository,
    TelegramAccountBindingUpsert,
)
from trms_backend.domain.telegram_bot import (
    TelegramBindingAuthorizationCreate,
    TelegramBindingAuthorizationRecord,
    TelegramBindingAuthorizationRepository,
    TelegramBindingAuthorizationStatus,
    TelegramBindingAuthorizationView,
)

TELEGRAM_BINDING_AUTHORIZATION_TTL = timedelta(minutes=15)


class TelegramBindingAuthorizationInvalidError(ValueError):
    def __init__(self) -> None:
        super().__init__("telegram binding authorization is invalid")


class TelegramBindingAuthorizationExpiredError(ValueError):
    def __init__(self) -> None:
        super().__init__("telegram binding authorization has expired")


class TelegramBindingAuthorizationConsumedError(ValueError):
    def __init__(self) -> None:
        super().__init__("telegram binding authorization has already been used")


@dataclass(frozen=True)
class TelegramBindingAuthorizationLink:
    token: str
    authorization: TelegramBindingAuthorizationRecord


class TelegramBindingOauthService:
    def __init__(
        self,
        authorization_repository: TelegramBindingAuthorizationRepository,
        binding_repository: TelegramAccountBindingRepository,
    ) -> None:
        self._authorization_repository = authorization_repository
        self._binding_repository = binding_repository

    def create_authorization(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: str | None,
    ) -> TelegramBindingAuthorizationLink:
        token = secrets.token_urlsafe(24)
        authorization = self._authorization_repository.create(
            TelegramBindingAuthorizationCreate(
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
                token_hash=_hash_binding_token(token),
                expires_at=datetime.now(UTC) + TELEGRAM_BINDING_AUTHORIZATION_TTL,
            )
        )
        return TelegramBindingAuthorizationLink(
            token=token,
            authorization=authorization,
        )

    def get_authorization_view(self, *, token: str) -> TelegramBindingAuthorizationView:
        authorization = self._get_authorization_by_token(token)
        return _build_authorization_view(authorization)

    def confirm_authorization(
        self,
        *,
        token: str,
        member_id: str,
    ):
        authorization = self._get_authorization_by_token(token)
        view = _build_authorization_view(authorization)
        if view.status is TelegramBindingAuthorizationStatus.EXPIRED:
            raise TelegramBindingAuthorizationExpiredError()
        if view.status is TelegramBindingAuthorizationStatus.CONSUMED:
            raise TelegramBindingAuthorizationConsumedError()
        binding = self._binding_repository.upsert(
            TelegramAccountBindingUpsert(
                telegram_user_id=authorization.telegram_user_id,
                member_id=member_id,
                telegram_username=authorization.telegram_username,
            )
        )
        self._authorization_repository.mark_consumed(
            authorization.id,
            consumed_at=datetime.now(UTC),
        )
        return binding

    def _get_authorization_by_token(self, token: str) -> TelegramBindingAuthorizationRecord:
        normalized_token = token.strip()
        if not normalized_token:
            raise TelegramBindingAuthorizationInvalidError()
        authorization = self._authorization_repository.get_by_token_hash(
            _hash_binding_token(normalized_token)
        )
        if authorization is None:
            raise TelegramBindingAuthorizationInvalidError()
        return authorization


def _hash_binding_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _build_authorization_view(
    authorization: TelegramBindingAuthorizationRecord,
) -> TelegramBindingAuthorizationView:
    now = datetime.now(UTC)
    if authorization.consumed_at is not None:
        status = TelegramBindingAuthorizationStatus.CONSUMED
    elif _normalize_utc_datetime(authorization.expires_at) < now:
        status = TelegramBindingAuthorizationStatus.EXPIRED
    else:
        status = TelegramBindingAuthorizationStatus.PENDING
    return TelegramBindingAuthorizationView(
        telegram_user_id=authorization.telegram_user_id,
        telegram_chat_id=authorization.telegram_chat_id,
        telegram_username=authorization.telegram_username,
        expires_at=authorization.expires_at,
        consumed_at=authorization.consumed_at,
        status=status,
    )


def _normalize_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
