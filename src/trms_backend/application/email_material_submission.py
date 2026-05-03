from __future__ import annotations

from email import policy
from email.parser import BytesParser
import re
from dataclasses import dataclass

from trms_backend.application.material_submission import (
    MaterialSubmissionBatchResult,
    MaterialUploadFailure,
    MaterialSubmissionService,
    MaterialSubmissionTaskNotFoundError,
    SubmittedMaterialFile,
)
from trms_backend.domain.email_bindings import (
    EmailSubmissionIdentityResolver,
    EmailSubmissionIdentityStatus,
)
from trms_backend.domain.materials import (
    MaterialType,
    SubmissionChannel,
    MaterialUploadEmailPackageMissingAttachmentsError,
    MaterialUploadEmailPackageUnreadableError,
)
from trms_backend.domain.tasks import ReimbursementTask, TaskRepository

ANGLE_BRACKET_TASK_PATTERN = re.compile(r"^<(?P<task_id>[^<>]+)>")
EMAIL_PACKAGE_CONTENT_TYPE = "message/rfc822"


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
        expanded_files, expansion_failures = expand_email_package_files(files)
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
                files=expanded_files,
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
                    files=expanded_files,
                    request_id=request_id,
                )
            except MaterialSubmissionTaskNotFoundError:
                batch_result = self._material_submission_service.submit_pending_assignment(
                    actor_id=normalized_resolved_member_id,
                    channel=SubmissionChannel.EMAIL,
                    material_type=parsed_email.material_type,
                    files=expanded_files,
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
            material_submission=MaterialSubmissionBatchResult(
                records=batch_result.records,
                failures=[*expansion_failures, *batch_result.failures],
            ),
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


def extract_email_body(message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_maintype() != "text":
                continue
            if part.get_content_subtype() != "plain":
                continue
            if part.get_content_disposition() == "attachment":
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


def extract_email_attachments(message) -> list[SubmittedMaterialFile]:
    attachments: list[SubmittedMaterialFile] = []
    for part in message.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        if filename is None:
            continue
        attachments.append(
            SubmittedMaterialFile(
                original_filename=filename,
                content_type=part.get_content_type(),
                content=part.get_payload(decode=True) or b"",
            )
        )
    return attachments


def expand_email_package_files(
    files: list[SubmittedMaterialFile],
) -> tuple[list[SubmittedMaterialFile], list[MaterialUploadFailure]]:
    expanded_files: list[SubmittedMaterialFile] = []
    failures: list[MaterialUploadFailure] = []
    for file in files:
        nested_files, nested_failures = _expand_single_email_package_file(file)
        expanded_files.extend(nested_files)
        failures.extend(nested_failures)
    return expanded_files, failures


def _expand_single_email_package_file(
    file: SubmittedMaterialFile,
) -> tuple[list[SubmittedMaterialFile], list[MaterialUploadFailure]]:
    if not _is_email_package_file(file):
        return [file], []

    try:
        parsed_message = BytesParser(policy=policy.default).parsebytes(file.content)
    except Exception:
        return [], [
            MaterialUploadFailure(
                original_filename=file.original_filename,
                error=MaterialUploadEmailPackageUnreadableError(file.original_filename),
            )
        ]

    nested_attachments = extract_email_attachments(parsed_message)
    if not nested_attachments:
        return [], [
            MaterialUploadFailure(
                original_filename=file.original_filename,
                error=MaterialUploadEmailPackageMissingAttachmentsError(file.original_filename),
            )
        ]

    return expand_email_package_files(nested_attachments)


def _is_email_package_file(file: SubmittedMaterialFile) -> bool:
    normalized_content_type = (file.content_type or "").split(";", maxsplit=1)[0].strip().lower()
    normalized_filename = (file.original_filename or "").strip().lower()
    return (
        normalized_content_type == EMAIL_PACKAGE_CONTENT_TYPE
        or normalized_filename.endswith(".eml")
    )


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
