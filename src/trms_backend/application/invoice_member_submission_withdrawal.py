from __future__ import annotations

from dataclasses import dataclass, field

from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
from trms_backend.domain.auth import UserRole
from trms_backend.domain.invoices import (
    InvoiceMemberSubmissionStatus,
    InvoiceRecord,
    InvoiceRepository,
)
from trms_backend.domain.materials import MaterialRepository
from trms_backend.domain.tasks import ReimbursementTask, TaskStatus


@dataclass(frozen=True)
class InvoiceMemberSubmissionWithdrawalFailure:
    invoice_id: str
    error_code: str
    detail: str


@dataclass(frozen=True)
class InvoiceMemberSubmissionWithdrawalBatchResult:
    items: list[InvoiceRecord] = field(default_factory=list)
    failures: list[InvoiceMemberSubmissionWithdrawalFailure] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.items and self.failures:
            return "partial_success"
        if self.items:
            return "success"
        return "failed"


class InvoiceMemberSubmissionWithdrawalService:
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

    def withdraw_batch(
        self,
        *,
        task: ReimbursementTask,
        actor_id: str,
        actor_role: UserRole,
        invoice_ids: list[str],
        request_id: str | None,
    ) -> InvoiceMemberSubmissionWithdrawalBatchResult:
        withdrawn_invoices: list[InvoiceRecord] = []
        failures: list[InvoiceMemberSubmissionWithdrawalFailure] = []

        for invoice_id in invoice_ids:
            invoice = self._invoice_repository.get(invoice_id)
            if invoice is None:
                failures.append(
                    InvoiceMemberSubmissionWithdrawalFailure(
                        invoice_id=invoice_id,
                        error_code="invoice_not_found",
                        detail="invoice not found",
                    )
                )
                continue
            if invoice.task_id != task.id:
                failure = InvoiceMemberSubmissionWithdrawalFailure(
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

            failure = self._validate_invoice_withdrawal(
                task=task,
                actor_id=actor_id,
                actor_role=actor_role,
                invoice=invoice,
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

            updated = self._invoice_repository.update_member_submission_status(
                invoice_id=invoice.id,
                status=InvoiceMemberSubmissionStatus.UNSUBMITTED,
                submitted_by_member_id=None,
                submitted_at=None,
            )
            if updated is None:
                failures.append(
                    InvoiceMemberSubmissionWithdrawalFailure(
                        invoice_id=invoice.id,
                        error_code="invoice_not_found",
                        detail="invoice not found",
                    )
                )
                continue
            withdrawn_invoices.append(updated)
            self._record_success_audit(
                actor_id=actor_id,
                invoice=updated,
                request_id=request_id,
            )

        return InvoiceMemberSubmissionWithdrawalBatchResult(
            items=withdrawn_invoices,
            failures=failures,
        )

    def _validate_invoice_withdrawal(
        self,
        *,
        task: ReimbursementTask,
        actor_id: str,
        actor_role: UserRole,
        invoice: InvoiceRecord,
    ) -> InvoiceMemberSubmissionWithdrawalFailure | None:
        if actor_role is not UserRole.MEMBER:
            return InvoiceMemberSubmissionWithdrawalFailure(
                invoice_id=invoice.id,
                error_code="actor_not_member",
                detail="only members can withdraw invoice submissions from the member workbench",
            )
        if task.status is not TaskStatus.OPEN:
            return InvoiceMemberSubmissionWithdrawalFailure(
                invoice_id=invoice.id,
                error_code="task_not_open",
                detail="task is not open for member invoice submission withdrawal",
            )
        material = self._material_repository.get(invoice.material_id)
        if material is None:
            return InvoiceMemberSubmissionWithdrawalFailure(
                invoice_id=invoice.id,
                error_code="invoice_material_not_found",
                detail="invoice material not found",
            )
        if material.submitter_id != actor_id:
            return InvoiceMemberSubmissionWithdrawalFailure(
                invoice_id=invoice.id,
                error_code="actor_not_invoice_submitter",
                detail="actor can only withdraw invoices created from own materials",
            )
        if invoice.member_submission_status is not InvoiceMemberSubmissionStatus.SUBMITTED:
            return InvoiceMemberSubmissionWithdrawalFailure(
                invoice_id=invoice.id,
                error_code="invoice_not_submitted",
                detail="invoice is not submitted",
            )
        if invoice.submitted_by_member_id != actor_id:
            return InvoiceMemberSubmissionWithdrawalFailure(
                invoice_id=invoice.id,
                error_code="actor_not_submission_owner",
                detail="actor can only withdraw invoice submissions created by self",
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
                action="withdraw_invoice_submission",
                result=AuditLogResult.SUCCEEDED,
                summary=f"withdraw invoice submission for invoice {invoice.id}",
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
        failure: InvoiceMemberSubmissionWithdrawalFailure,
        request_id: str | None,
    ) -> None:
        self._audit_log_repository.create(
            AuditLogCreate(
                actor_id=actor_id,
                object_type="invoice",
                object_id=invoice.id,
                action="withdraw_invoice_submission",
                result=AuditLogResult.REJECTED,
                summary=f"reject invoice submission withdrawal for invoice {invoice.id}",
                detail={
                    "failure_reason": failure.detail,
                    "error_code": failure.error_code,
                    "member_submission_status": invoice.member_submission_status,
                    "submitted_by_member_id": invoice.submitted_by_member_id,
                },
                task_id=task_id,
                request_id=request_id,
            )
        )
