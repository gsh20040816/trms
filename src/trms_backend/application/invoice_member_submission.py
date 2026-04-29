from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
from trms_backend.domain.auth import UserRole
from trms_backend.domain.confirmations import ConfirmationRecord
from trms_backend.domain.invoices import (
    InvoiceMemberSubmissionStatus,
    InvoiceRecord,
    InvoiceRepository,
    ValidationResult,
)
from trms_backend.domain.materials import MaterialRecord, MaterialRepository
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.tasks import (
    ReimbursementTask,
    TaskReviewValidationError,
    TaskStatus,
    ensure_task_can_enter_ready_to_export,
)


@dataclass(frozen=True)
class InvoiceMemberSubmissionFailure:
    invoice_id: str
    error_code: str
    detail: str


@dataclass(frozen=True)
class InvoiceMemberSubmissionBatchResult:
    items: list[InvoiceRecord] = field(default_factory=list)
    failures: list[InvoiceMemberSubmissionFailure] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.items and self.failures:
            return "partial_success"
        if self.items:
            return "success"
        return "failed"


class InvoiceMemberSubmissionService:
    def __init__(
        self,
        *,
        material_repository: MaterialRepository,
        invoice_repository: InvoiceRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._material_repository = material_repository
        self._invoice_repository = invoice_repository
        self._audit_log_repository = audit_log_repository

    def submit_batch(
        self,
        *,
        task: ReimbursementTask,
        actor_id: str,
        actor_role: UserRole,
        invoice_ids: list[str],
        validations_by_invoice_id: dict[str, list[ValidationResult]],
        splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
        confirmations_by_split_id: dict[str, ConfirmationRecord],
        request_id: str | None,
    ) -> InvoiceMemberSubmissionBatchResult:
        submitted_invoices: list[InvoiceRecord] = []
        failures: list[InvoiceMemberSubmissionFailure] = []

        for invoice_id in invoice_ids:
            invoice = self._invoice_repository.get(invoice_id)
            if invoice is None:
                failures.append(
                    InvoiceMemberSubmissionFailure(
                        invoice_id=invoice_id,
                        error_code="invoice_not_found",
                        detail="invoice not found",
                    )
                )
                continue
            if invoice.task_id != task.id:
                failure = InvoiceMemberSubmissionFailure(
                    invoice_id=invoice_id,
                    error_code="invoice_belongs_to_different_task",
                    detail="invoice belongs to a different task",
                )
                failures.append(failure)
                self._record_rejection_audit(
                    actor_id=actor_id,
                    invoice=invoice,
                    task_id=task.id,
                    failure=failure,
                    request_id=request_id,
                )
                continue

            failure = self._validate_invoice_submission(
                task=task,
                actor_id=actor_id,
                actor_role=actor_role,
                invoice=invoice,
                validations_by_invoice_id=validations_by_invoice_id,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
            )
            if failure is not None:
                failures.append(failure)
                self._record_rejection_audit(
                    actor_id=actor_id,
                    invoice=invoice,
                    task_id=task.id,
                    failure=failure,
                    request_id=request_id,
                )
                continue

            submitted_at = datetime.now(timezone.utc)
            updated = self._invoice_repository.update_member_submission_status(
                invoice_id=invoice.id,
                status=InvoiceMemberSubmissionStatus.SUBMITTED,
                submitted_by_member_id=actor_id,
                submitted_at=submitted_at,
            )
            if updated is None:
                failures.append(
                    InvoiceMemberSubmissionFailure(
                        invoice_id=invoice.id,
                        error_code="invoice_not_found",
                        detail="invoice not found",
                    )
                )
                continue
            submitted_invoices.append(updated)
            self._record_success_audit(
                actor_id=actor_id,
                invoice=updated,
                request_id=request_id,
            )

        return InvoiceMemberSubmissionBatchResult(
            items=submitted_invoices,
            failures=failures,
        )

    def _validate_invoice_submission(
        self,
        *,
        task: ReimbursementTask,
        actor_id: str,
        actor_role: UserRole,
        invoice: InvoiceRecord,
        validations_by_invoice_id: dict[str, list[ValidationResult]],
        splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
        confirmations_by_split_id: dict[str, ConfirmationRecord],
    ) -> InvoiceMemberSubmissionFailure | None:
        if actor_role is not UserRole.MEMBER:
            return InvoiceMemberSubmissionFailure(
                invoice_id=invoice.id,
                error_code="actor_not_member",
                detail="only members can submit invoices from the member workbench",
            )
        if task.status is not TaskStatus.OPEN:
            return InvoiceMemberSubmissionFailure(
                invoice_id=invoice.id,
                error_code="task_not_open",
                detail="task is not open for member invoice submission",
            )
        material = self._material_repository.get(invoice.material_id)
        if material is None:
            return InvoiceMemberSubmissionFailure(
                invoice_id=invoice.id,
                error_code="invoice_material_not_found",
                detail="invoice material not found",
            )
        if material.submitter_id != actor_id:
            return InvoiceMemberSubmissionFailure(
                invoice_id=invoice.id,
                error_code="actor_not_invoice_submitter",
                detail="actor can only submit invoices created from own materials",
            )
        if invoice.member_submission_status is InvoiceMemberSubmissionStatus.SUBMITTED:
            return InvoiceMemberSubmissionFailure(
                invoice_id=invoice.id,
                error_code="invoice_already_submitted",
                detail="invoice is already submitted",
            )

        try:
            ensure_task_can_enter_ready_to_export(
                [invoice],
                validations_by_invoice_id=validations_by_invoice_id,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
                pending_assignment_material_ids=[],
            )
        except TaskReviewValidationError as error:
            return InvoiceMemberSubmissionFailure(
                invoice_id=invoice.id,
                error_code="invoice_not_ready_for_submission",
                detail="; ".join(error.reasons),
            )
        return None

    def _record_success_audit(
        self,
        *,
        actor_id: str,
        invoice: InvoiceRecord,
        request_id: str | None,
    ) -> None:
        self._audit_log_repository.create(
            AuditLogCreate(
                actor_id=actor_id,
                object_type="invoice",
                object_id=invoice.id,
                action="submit_invoice_for_review",
                result=AuditLogResult.SUCCEEDED,
                summary=f"submit invoice {invoice.id} for member review handoff",
                detail={
                    "member_submission_status": invoice.member_submission_status,
                    "submitted_by_member_id": invoice.submitted_by_member_id,
                    "submitted_at": invoice.submitted_at,
                },
                task_id=invoice.task_id,
                request_id=request_id,
            )
        )

    def _record_rejection_audit(
        self,
        *,
        actor_id: str,
        invoice: InvoiceRecord,
        task_id: str,
        failure: InvoiceMemberSubmissionFailure,
        request_id: str | None,
    ) -> None:
        self._audit_log_repository.create(
            AuditLogCreate(
                actor_id=actor_id,
                object_type="invoice",
                object_id=invoice.id,
                action="submit_invoice_for_review",
                result=AuditLogResult.REJECTED,
                summary=f"reject invoice submission for invoice {invoice.id}",
                detail={
                    "failure_reason": failure.detail,
                    "error_code": failure.error_code,
                    "member_submission_status": invoice.member_submission_status,
                },
                task_id=task_id,
                request_id=request_id,
            )
        )
