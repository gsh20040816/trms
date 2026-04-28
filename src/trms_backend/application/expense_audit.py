from __future__ import annotations

from trms_backend.domain.audit_logs import AuditLogCreate, AuditLogRepository, AuditLogResult
from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.splits import ExpenseSplitRecord


def record_invoice_split_replace_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    invoice_id: str,
    task_id: str,
    previous_splits: list[ExpenseSplitRecord],
    current_splits: list[ExpenseSplitRecord],
    request_id: str | None,
) -> None:
    audit_log_repository.create(
        AuditLogCreate(
            actor_id=actor_id,
            object_type="invoice",
            object_id=invoice_id,
            action="replace_invoice_splits",
            result=AuditLogResult.SUCCEEDED,
            summary=f"replace invoice splits for invoice {invoice_id}",
            detail={
                "previous_split_count": len(previous_splits),
                "current_split_count": len(current_splits),
                "changed_splits": _build_split_change_items(previous_splits, current_splits),
            },
            task_id=task_id,
            request_id=request_id,
        )
    )


def record_split_confirmation_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    split: ExpenseSplitRecord,
    invoice_id: str,
    task_id: str,
    confirmation: ConfirmationRecord,
    previous_confirmation: ConfirmationRecord | None,
    request_id: str | None,
) -> None:
    audit_log_repository.create(
        AuditLogCreate(
            actor_id=actor_id,
            object_type="expense_split",
            object_id=split.id,
            action=_resolve_confirmation_action(
                actor_id=actor_id,
                confirmation=confirmation,
                previous_confirmation=previous_confirmation,
            ),
            result=AuditLogResult.SUCCEEDED,
            summary=f"record {confirmation.status} confirmation for split {split.id}",
            detail={
                "invoice_id": invoice_id,
                "member_id": confirmation.member_id,
                "status": confirmation.status,
                "dispute_reason": confirmation.dispute_reason,
                "previous_status": (
                    previous_confirmation.status if previous_confirmation is not None else None
                ),
                "previous_dispute_reason": (
                    previous_confirmation.dispute_reason
                    if previous_confirmation is not None
                    else None
                ),
                "split_version": confirmation.split_version,
                "split_amount_cents": confirmation.split_amount_cents,
                "split_note": confirmation.split_note,
            },
            task_id=task_id,
            request_id=request_id,
        )
    )


def record_split_confirmation_rejection_audit(
    audit_log_repository: AuditLogRepository,
    *,
    actor_id: str,
    split: ExpenseSplitRecord,
    invoice_id: str,
    task_id: str,
    requested_member_id: str,
    requested_status: ConfirmationStatus,
    dispute_reason: str | None,
    failure_reason: str,
    request_id: str | None,
) -> None:
    audit_log_repository.create(
        AuditLogCreate(
            actor_id=actor_id,
            object_type="expense_split",
            object_id=split.id,
            action="submit_split_confirmation",
            result=AuditLogResult.REJECTED,
            summary=f"reject confirmation update for split {split.id}",
            detail={
                "invoice_id": invoice_id,
                "requested_member_id": requested_member_id,
                "requested_status": requested_status,
                "dispute_reason": dispute_reason,
                "split_member_id": split.member_id,
                "split_version": split.version,
                "failure_reason": failure_reason,
            },
            task_id=task_id,
            request_id=request_id,
        )
    )


def _build_split_change_items(
    previous_splits: list[ExpenseSplitRecord],
    current_splits: list[ExpenseSplitRecord],
) -> list[dict[str, object]]:
    previous_by_member_id = {item.member_id: item for item in previous_splits}
    current_by_member_id = {item.member_id: item for item in current_splits}

    changed_items: list[dict[str, object]] = []
    for member_id in sorted(set(previous_by_member_id) | set(current_by_member_id)):
        previous = previous_by_member_id.get(member_id)
        current = current_by_member_id.get(member_id)
        if previous is None and current is not None:
            changed_items.append(
                {
                    "member_id": member_id,
                    "change_type": "added",
                    "before": None,
                    "after": _serialize_split(current),
                }
            )
            continue
        if previous is not None and current is None:
            changed_items.append(
                {
                    "member_id": member_id,
                    "change_type": "removed",
                    "before": _serialize_split(previous),
                    "after": None,
                }
            )
            continue
        if previous is None or current is None:
            continue
        if (
            previous.amount_cents == current.amount_cents
            and previous.note == current.note
            and previous.version == current.version
        ):
            continue
        changed_items.append(
            {
                "member_id": member_id,
                "change_type": "updated",
                "before": _serialize_split(previous),
                "after": _serialize_split(current),
            }
        )
    return changed_items


def _serialize_split(split: ExpenseSplitRecord) -> dict[str, object]:
    return {
        "split_id": split.id,
        "member_id": split.member_id,
        "amount_cents": split.amount_cents,
        "note": split.note,
        "version": split.version,
        "is_active": split.is_active,
    }


def _resolve_confirmation_action(
    *,
    actor_id: str,
    confirmation: ConfirmationRecord,
    previous_confirmation: ConfirmationRecord | None,
) -> str:
    if (
        confirmation.status is ConfirmationStatus.PENDING
        and previous_confirmation is not None
        and previous_confirmation.status is ConfirmationStatus.DISPUTED
        and actor_id != confirmation.member_id
    ):
        return "resolve_split_dispute"
    if confirmation.status is ConfirmationStatus.DISPUTED:
        return "dispute_expense_split"
    if confirmation.status is ConfirmationStatus.CONFIRMED:
        return "confirm_expense_split"
    return "submit_split_confirmation"
