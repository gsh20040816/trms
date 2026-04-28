from __future__ import annotations

from dataclasses import dataclass

from trms_backend.application.material_submission import (
    MaterialSubmissionBatchResult,
    MaterialSubmissionService,
    SubmittedMaterialFile,
)
from trms_backend.domain.materials import MaterialType, SubmissionChannel
from trms_backend.domain.telegram_bindings import (
    TelegramAccountBindingRepository,
    TelegramSubmissionIdentity,
    TelegramSubmissionIdentityResolver,
    TelegramSubmissionIdentityStatus,
)


@dataclass(frozen=True)
class TelegramMaterialSubmissionResult:
    submission_identity: TelegramSubmissionIdentity
    material_submission: MaterialSubmissionBatchResult


class TelegramMaterialSubmissionService:
    def __init__(
        self,
        binding_repository: TelegramAccountBindingRepository,
        material_submission_service: MaterialSubmissionService,
    ) -> None:
        self._submission_identity_resolver = TelegramSubmissionIdentityResolver(binding_repository)
        self._material_submission_service = material_submission_service

    def submit(
        self,
        *,
        telegram_user_id: int,
        telegram_username: str | None,
        task_id: str | None,
        material_type: MaterialType,
        files: list[SubmittedMaterialFile],
        request_id: str | None = None,
    ) -> TelegramMaterialSubmissionResult:
        normalized_task_id = _normalize_optional_string(task_id)
        submission_identity = self._submission_identity_resolver.resolve(telegram_user_id)
        actor_id = _build_actor_id(
            submission_identity=submission_identity,
            telegram_user_id=telegram_user_id,
        )

        if (
            submission_identity.status is TelegramSubmissionIdentityStatus.BOUND
            and normalized_task_id is not None
        ):
            assert submission_identity.member_id is not None
            batch_result = self._material_submission_service.submit_to_task(
                task_id=normalized_task_id,
                submitter_id=submission_identity.member_id,
                actor_id=actor_id,
                channel=SubmissionChannel.TELEGRAM,
                material_type=material_type,
                files=files,
                request_id=request_id,
            )
        else:
            batch_result = self._material_submission_service.submit_pending_assignment(
                actor_id=actor_id,
                channel=SubmissionChannel.TELEGRAM,
                material_type=material_type,
                files=files,
                task_id_hint=normalized_task_id,
                submitter_id_hint=_build_submitter_hint(
                    submission_identity=submission_identity,
                    telegram_user_id=telegram_user_id,
                    telegram_username=telegram_username,
                ),
                request_id=request_id,
            )

        return TelegramMaterialSubmissionResult(
            submission_identity=submission_identity,
            material_submission=batch_result,
        )


def _build_submitter_hint(
    *,
    submission_identity: TelegramSubmissionIdentity,
    telegram_user_id: int,
    telegram_username: str | None,
) -> str:
    if submission_identity.member_id is not None:
        return submission_identity.member_id

    normalized_username = _normalize_telegram_username(telegram_username)
    if normalized_username is None:
        return f"telegram_user_id:{telegram_user_id}"
    return f"telegram_user_id:{telegram_user_id} (@{normalized_username})"


def _build_actor_id(
    *,
    submission_identity: TelegramSubmissionIdentity,
    telegram_user_id: int,
) -> str:
    if submission_identity.member_id is not None:
        return submission_identity.member_id
    return f"telegram_user_id:{telegram_user_id}"


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_telegram_username(value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    stripped = normalized.lstrip("@").lower()
    return stripped or None
