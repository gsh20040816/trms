from __future__ import annotations

from trms_backend.domain.confirmations import (
    ConfirmationRepository,
    ConfirmationStatus,
    ConfirmationSubmit,
)
from trms_backend.domain.invoices import InvoiceRecord
from trms_backend.domain.materials import MaterialRecord
from trms_backend.domain.splits import ExpenseSplitItem, ExpenseSplitRecord, ExpenseSplitRepository


class InvoiceSplitDefaultService:
    def __init__(
        self,
        *,
        split_repository: ExpenseSplitRepository,
        confirmation_repository: ConfirmationRepository,
    ) -> None:
        self._split_repository = split_repository
        self._confirmation_repository = confirmation_repository

    def ensure_default_self_split(
        self,
        *,
        invoice: InvoiceRecord,
        material: MaterialRecord,
    ) -> list[ExpenseSplitRecord]:
        if material.submitter_id is None:
            return self._split_repository.list_by_invoice(invoice.id)

        current_splits = self._split_repository.list_by_invoice(invoice.id)
        if current_splits:
            return current_splits

        created_splits = self._split_repository.replace_for_invoice(
            invoice.id,
            [
                ExpenseSplitItem(
                    member_id=material.submitter_id,
                    amount_cents=invoice.amount_cents,
                    note=None,
                )
            ],
        )
        self.confirm_actor_own_splits(
            actor_id=material.submitter_id,
            splits=created_splits,
        )
        return created_splits

    def confirm_actor_own_splits(
        self,
        *,
        actor_id: str,
        splits: list[ExpenseSplitRecord],
    ) -> None:
        normalized_actor_id = actor_id.strip()
        for split in splits:
            if split.member_id != normalized_actor_id:
                continue
            self._confirmation_repository.upsert_for_split(
                split.id,
                ConfirmationSubmit(
                    actor_id=normalized_actor_id,
                    member_id=normalized_actor_id,
                    status=ConfirmationStatus.CONFIRMED,
                ),
            )
