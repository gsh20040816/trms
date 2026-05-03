from __future__ import annotations

import re
from dataclasses import dataclass

from trms_backend.application.material_submission import (
    MaterialSubmissionBatchResult,
    MaterialSubmissionService,
    MaterialSubmissionTaskNotFoundError,
    SubmittedMaterialFile,
)
from trms_backend.domain.email_bindings import (
    EmailSubmissionIdentityResolver,
    EmailSubmissionIdentityStatus,
)
from trms_backend.domain.materials import MaterialType, SubmissionChannel
from trms_backend.domain.tasks import ReimbursementTask, TaskRepository

ANGLE_BRACKET_TASK_PATTERN = re.compile(r"^<(?P<task_id>[^<>]+)>")


@dataclass(frozen=True)
class ParsedEmailSubmission:
    sender_email: str
    task_id: str
    submitted_task_key: str
    material_type: MaterialType
    metadata_submitter_id: str | None
    note: str | None


@dataclass(frozen=True)
class EmailMaterialSubmissionResult:
    parsed_email: ParsedEmailSubmission
    material_submission: MaterialSubmissionBatchResult


class EmailMaterialSubmissionFormatError(ValueError):
    def __init__(self, *, error_code: str, detail: str) -> None:
        self.error_code = error_code
        super().__init__(detail)


class EmailMaterialSubmissionService:
    def __init__(
        self,
        material_submission_service: MaterialSubmissionService,
        task_repository: TaskRepository,
        submission_identity_resolver: EmailSubmissionIdentityResolver | None = None,
    ) -> None:
        self._material_submission_service = material_submission_service
        self._task_repository = task_repository
        self._submission_identity_resolver = submission_identity_resolver

    def submit(
        self,
        *,
        sender_email: str,
        subject: str,
        body: str,
        resolved_member_id: str | None,
        files: list[SubmittedMaterialFile],
        request_id: str | None = None,
    ) -> EmailMaterialSubmissionResult:
        parsed_email = parse_formatted_email_submission(
            sender_email=sender_email,
            subject=subject,
            body=body,
            task_repository=self._task_repository,
        )
        normalized_resolved_member_id = _normalize_optional_string(resolved_member_id)
        if normalized_resolved_member_id is None and self._submission_identity_resolver is not None:
            resolved_identity = self._submission_identity_resolver.resolve(parsed_email.sender_email)
            if resolved_identity.status is EmailSubmissionIdentityStatus.BOUND:
                normalized_resolved_member_id = resolved_identity.member_id

        if normalized_resolved_member_id is None:
            batch_result = self._material_submission_service.submit_pending_assignment(
                actor_id=f"email:{parsed_email.sender_email}",
                channel=SubmissionChannel.EMAIL,
                material_type=parsed_email.material_type,
                files=files,
                task_id_hint=parsed_email.submitted_task_key,
                submitter_id_hint=_build_submitter_hint(
                    sender_email=parsed_email.sender_email,
                    metadata_submitter_id=parsed_email.metadata_submitter_id,
                    resolved_member_id=None,
                ),
                request_id=request_id,
            )
        else:
            try:
                batch_result = self._material_submission_service.submit_to_task(
                    task_id=parsed_email.task_id,
                    submitter_id=normalized_resolved_member_id,
                    actor_id=normalized_resolved_member_id,
                    channel=SubmissionChannel.EMAIL,
                    material_type=parsed_email.material_type,
                    files=files,
                    request_id=request_id,
                )
            except MaterialSubmissionTaskNotFoundError:
                batch_result = self._material_submission_service.submit_pending_assignment(
                    actor_id=normalized_resolved_member_id,
                    channel=SubmissionChannel.EMAIL,
                    material_type=parsed_email.material_type,
                    files=files,
                    task_id_hint=parsed_email.submitted_task_key,
                    submitter_id_hint=_build_submitter_hint(
                        sender_email=parsed_email.sender_email,
                        metadata_submitter_id=parsed_email.metadata_submitter_id,
                        resolved_member_id=normalized_resolved_member_id,
                    ),
                    request_id=request_id,
                )

        return EmailMaterialSubmissionResult(
            parsed_email=parsed_email,
            material_submission=batch_result,
        )


def parse_formatted_email_submission(
    *,
    sender_email: str,
    subject: str,
    body: str,
    task_repository: TaskRepository,
) -> ParsedEmailSubmission:
    normalized_sender_email = _normalize_sender_email(sender_email)
    submitted_task_key = _parse_subject(subject)
    resolved_task = _resolve_email_target_task(
        submitted_task_key=submitted_task_key,
        task_repository=task_repository,
    )
    return ParsedEmailSubmission(
        sender_email=normalized_sender_email,
        task_id=resolved_task.id if resolved_task is not None else submitted_task_key,
        submitted_task_key=submitted_task_key,
        material_type=MaterialType.OTHER_ATTACHMENT,
        metadata_submitter_id=None,
        note=None,
    )


def _parse_subject(subject: str) -> str:
    normalized_subject = subject.strip()
    angle_bracket_match = ANGLE_BRACKET_TASK_PATTERN.match(normalized_subject)
    if angle_bracket_match is not None:
        task_id = angle_bracket_match.group("task_id").strip().lower()
        if not task_id or re.search(r"\s", task_id):
            raise EmailMaterialSubmissionFormatError(
                error_code="missing_task_id",
                detail="email subject angle-bracket task marker must be non-empty",
            )
        return task_id

    raise EmailMaterialSubmissionFormatError(
        error_code="invalid_subject_prefix",
        detail="email subject must start with <task_key>",
    )


def _build_submitter_hint(
    *,
    sender_email: str,
    metadata_submitter_id: str | None,
    resolved_member_id: str | None,
) -> str:
    if resolved_member_id is not None:
        return resolved_member_id

    sender_hint = f"email:{sender_email}"
    if metadata_submitter_id is None:
        return sender_hint
    return f"{sender_hint} (submitter_id:{metadata_submitter_id})"


def _normalize_sender_email(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise EmailMaterialSubmissionFormatError(
            error_code="missing_metadata_block",
            detail="sender_email must not be empty",
        )
    return normalized


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _resolve_email_target_task(
    *,
    submitted_task_key: str,
    task_repository: TaskRepository,
) -> ReimbursementTask | None:
    task = task_repository.get_by_email_submission_key(submitted_task_key)
    if task is not None:
        return task
    return task_repository.get(submitted_task_key)
