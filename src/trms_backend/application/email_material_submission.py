from __future__ import annotations

import re
from dataclasses import dataclass

from trms_backend.application.material_submission import (
    MaterialSubmissionBatchResult,
    MaterialSubmissionService,
    MaterialSubmissionTaskNotFoundError,
    SubmittedMaterialFile,
)
from trms_backend.domain.materials import MaterialType, SubmissionChannel

SUBJECT_PREFIX = "[TRMS] "
TASK_MARKER = "task:"
OTHER_ATTACHMENT_EMAIL_ALIAS = "other"
METADATA_LINE_PATTERN = re.compile(r"^(?P<key>[a-z_]+):(?P<value>.*)$")
SUPPORTED_METADATA_KEYS = frozenset({"material_type", "submitter_id", "task_id", "note"})


@dataclass(frozen=True)
class ParsedEmailSubmission:
    sender_email: str
    task_id: str
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
    def __init__(self, material_submission_service: MaterialSubmissionService) -> None:
        self._material_submission_service = material_submission_service

    def submit(
        self,
        *,
        sender_email: str,
        subject: str,
        body: str,
        resolved_member_id: str | None,
        files: list[SubmittedMaterialFile],
    ) -> EmailMaterialSubmissionResult:
        parsed_email = parse_formatted_email_submission(
            sender_email=sender_email,
            subject=subject,
            body=body,
        )
        normalized_resolved_member_id = _normalize_optional_string(resolved_member_id)

        if normalized_resolved_member_id is None:
            batch_result = self._material_submission_service.submit_pending_assignment(
                channel=SubmissionChannel.EMAIL,
                material_type=parsed_email.material_type,
                files=files,
                task_id_hint=parsed_email.task_id,
                submitter_id_hint=_build_submitter_hint(
                    sender_email=parsed_email.sender_email,
                    metadata_submitter_id=parsed_email.metadata_submitter_id,
                    resolved_member_id=None,
                ),
            )
        else:
            try:
                batch_result = self._material_submission_service.submit_to_task(
                    task_id=parsed_email.task_id,
                    submitter_id=normalized_resolved_member_id,
                    channel=SubmissionChannel.EMAIL,
                    material_type=parsed_email.material_type,
                    files=files,
                )
            except MaterialSubmissionTaskNotFoundError:
                batch_result = self._material_submission_service.submit_pending_assignment(
                    channel=SubmissionChannel.EMAIL,
                    material_type=parsed_email.material_type,
                    files=files,
                    task_id_hint=parsed_email.task_id,
                    submitter_id_hint=_build_submitter_hint(
                        sender_email=parsed_email.sender_email,
                        metadata_submitter_id=parsed_email.metadata_submitter_id,
                        resolved_member_id=normalized_resolved_member_id,
                    ),
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
) -> ParsedEmailSubmission:
    normalized_sender_email = _normalize_sender_email(sender_email)
    task_id = _parse_subject(subject)
    metadata = _parse_metadata_block(body)
    metadata_task_id = _normalize_optional_string(metadata.get("task_id"))
    if metadata_task_id is not None and metadata_task_id != task_id:
        raise EmailMaterialSubmissionFormatError(
            error_code="task_id_mismatch",
            detail="metadata task_id does not match subject task_id",
        )

    material_type = _parse_material_type(metadata.get("material_type"))
    return ParsedEmailSubmission(
        sender_email=normalized_sender_email,
        task_id=task_id,
        material_type=material_type,
        metadata_submitter_id=_normalize_optional_string(metadata.get("submitter_id")),
        note=_normalize_optional_string(metadata.get("note")),
    )


def _parse_subject(subject: str) -> str:
    normalized_subject = subject.strip()
    if not normalized_subject.startswith(SUBJECT_PREFIX):
        raise EmailMaterialSubmissionFormatError(
            error_code="invalid_subject_prefix",
            detail="email subject must start with [TRMS]",
        )

    marker_count = normalized_subject.count(TASK_MARKER)
    if marker_count == 0:
        raise EmailMaterialSubmissionFormatError(
            error_code="missing_task_id",
            detail="email subject must include task:<task_id>",
        )
    if marker_count > 1:
        raise EmailMaterialSubmissionFormatError(
            error_code="duplicate_task_id_marker",
            detail="email subject must include exactly one task: marker",
        )

    task_segment = normalized_subject[len(SUBJECT_PREFIX) :]
    if not task_segment.startswith(TASK_MARKER):
        raise EmailMaterialSubmissionFormatError(
            error_code="missing_task_id",
            detail="email subject must include task:<task_id>",
        )

    task_id = task_segment[len(TASK_MARKER) :].strip()
    if not task_id or re.search(r"\s", task_id):
        raise EmailMaterialSubmissionFormatError(
            error_code="missing_task_id",
            detail="email subject must include a non-empty task_id",
        )
    return task_id


def _parse_metadata_block(body: str) -> dict[str, str]:
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    metadata: dict[str, str] = {}
    saw_metadata_line = False

    for line in lines:
        if not line.strip():
            break
        match = METADATA_LINE_PATTERN.match(line)
        if match is None:
            if not saw_metadata_line:
                raise EmailMaterialSubmissionFormatError(
                    error_code="missing_metadata_block",
                    detail="email body must start with a metadata block",
                )
            break

        saw_metadata_line = True
        key = match.group("key")
        if key not in SUPPORTED_METADATA_KEYS:
            continue
        metadata[key] = match.group("value").strip()

    if not saw_metadata_line:
        raise EmailMaterialSubmissionFormatError(
            error_code="missing_metadata_block",
            detail="email body must start with a metadata block",
        )
    return metadata


def _parse_material_type(value: str | None) -> MaterialType:
    normalized_value = _normalize_optional_string(value)
    if normalized_value is None:
        raise EmailMaterialSubmissionFormatError(
            error_code="missing_material_type",
            detail="email metadata must include material_type",
        )

    if normalized_value == OTHER_ATTACHMENT_EMAIL_ALIAS:
        return MaterialType.OTHER_ATTACHMENT

    try:
        return MaterialType(normalized_value)
    except ValueError as error:
        raise EmailMaterialSubmissionFormatError(
            error_code="unsupported_material_type",
            detail=f"unsupported email material_type: {normalized_value}",
        ) from error


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
