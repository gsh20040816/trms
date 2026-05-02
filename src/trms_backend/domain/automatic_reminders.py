from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.invoices import InvoiceRecord, ValidationResult
from trms_backend.domain.materials import MaterialRecord
from trms_backend.domain.missing_materials import aggregate_task_missing_materials
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.tasks import ReimbursementTask, ensure_task_administrator


class AutomaticReminderTaskStatus(StrEnum):
    PENDING = "pending"


class AutomaticReminderTaskKind(StrEnum):
    MISSING_MATERIALS = "missing_materials"
    UNCONFIRMED_EXPENSES = "unconfirmed_expenses"


class AutomaticReminderTaskGenerate(BaseModel):
    actor_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_text(self) -> AutomaticReminderTaskGenerate:
        self.actor_id = self.actor_id.strip()
        return self


class AutomaticReminderTaskCreate(BaseModel):
    requested_by: str = Field(min_length=1)
    member_id: str = Field(min_length=1)
    kind: AutomaticReminderTaskKind
    summary: str = Field(min_length=1, max_length=2000)
    payload: dict[str, Any] = Field(default_factory=dict)
    deduplication_key: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def normalize_text(self) -> AutomaticReminderTaskCreate:
        self.requested_by = self.requested_by.strip()
        self.member_id = self.member_id.strip()
        self.summary = self.summary.strip()
        self.deduplication_key = self.deduplication_key.strip()
        return self


class AutomaticReminderTaskRecord(BaseModel):
    id: str
    task_id: str
    member_id: str
    requested_by: str
    kind: AutomaticReminderTaskKind
    status: AutomaticReminderTaskStatus
    summary: str
    payload: dict[str, Any]
    deduplication_key: str
    created_at: datetime
    updated_at: datetime


class AutomaticReminderTaskGenerationResult(BaseModel):
    created_count: int
    reused_count: int
    items: list[AutomaticReminderTaskRecord]


class AutomaticReminderTaskActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to manage automatic reminder tasks for this task")


class AutomaticReminderTaskRepository(Protocol):
    def create(
        self,
        *,
        task_id: str,
        data: AutomaticReminderTaskCreate,
    ) -> AutomaticReminderTaskRecord:
        raise NotImplementedError

    def get_by_deduplication_key(
        self,
        *,
        task_id: str,
        deduplication_key: str,
    ) -> AutomaticReminderTaskRecord | None:
        raise NotImplementedError

    def list_by_task(self, task_id: str) -> list[AutomaticReminderTaskRecord]:
        raise NotImplementedError


def ensure_task_automatic_reminder_administrator(
    task: ReimbursementTask,
    *,
    actor_id: str,
) -> str:
    return ensure_task_administrator(
        task,
        actor_id=actor_id,
        error_type=AutomaticReminderTaskActorNotAllowedError,
    )


def generate_task_automatic_reminder_tasks(
    task: ReimbursementTask,
    *,
    payload: AutomaticReminderTaskGenerate,
    repository: AutomaticReminderTaskRepository,
    materials: list[MaterialRecord],
    invoices: list[InvoiceRecord],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
) -> AutomaticReminderTaskGenerationResult:
    requested_by = ensure_task_automatic_reminder_administrator(task, actor_id=payload.actor_id)
    materials_by_id = {material.id: material for material in materials}
    candidates = _build_missing_material_candidates(
        task=task,
        requested_by=requested_by,
        invoices=invoices,
        materials_by_id=materials_by_id,
        validations_by_invoice_id=validations_by_invoice_id,
    )
    candidates.extend(
        _build_unconfirmed_expense_candidates(
            task=task,
            requested_by=requested_by,
            invoices=invoices,
            splits_by_invoice_id=splits_by_invoice_id,
            confirmations_by_split_id=confirmations_by_split_id,
        )
    )

    created_count = 0
    reused_count = 0
    items: list[AutomaticReminderTaskRecord] = []
    for candidate in candidates:
        existing = repository.get_by_deduplication_key(
            task_id=task.id,
            deduplication_key=candidate.deduplication_key,
        )
        if existing is not None:
            reused_count += 1
            items.append(existing)
            continue
        created_count += 1
        items.append(repository.create(task_id=task.id, data=candidate))

    return AutomaticReminderTaskGenerationResult(
        created_count=created_count,
        reused_count=reused_count,
        items=items,
    )


def list_task_automatic_reminder_tasks(
    task: ReimbursementTask,
    *,
    actor_id: str,
    repository: AutomaticReminderTaskRepository,
) -> list[AutomaticReminderTaskRecord]:
    ensure_task_automatic_reminder_administrator(task, actor_id=actor_id)
    return repository.list_by_task(task.id)


def _build_missing_material_candidates(
    *,
    task: ReimbursementTask,
    requested_by: str,
    invoices: list[InvoiceRecord],
    materials_by_id: dict[str, MaterialRecord],
    validations_by_invoice_id: dict[str, list[ValidationResult]],
) -> list[AutomaticReminderTaskCreate]:
    missing_materials = aggregate_task_missing_materials(
        task_id=task.id,
        invoices=invoices,
        materials_by_id=materials_by_id,
        validations_by_invoice_id=validations_by_invoice_id,
    )
    candidates: list[AutomaticReminderTaskCreate] = []
    for member in sorted(missing_materials.members, key=lambda item: item.member_id):
        payload = {
            "invoice_ids": list(dict.fromkeys(item.invoice_id for item in member.items)),
            "invoice_numbers": list(dict.fromkeys(item.invoice_number for item in member.items)),
            "required_material_types": [
                item.required_material_type.value for item in member.items
            ],
            "rule_codes": [item.source_rule_code for item in member.items],
            "item_count": len(member.items),
        }
        summary = (
            "系统检测到缺失材料，请补充："
            + "、".join(dict.fromkeys(payload["required_material_types"]))
        )
        candidates.append(
            AutomaticReminderTaskCreate(
                requested_by=requested_by,
                member_id=member.member_id,
                kind=AutomaticReminderTaskKind.MISSING_MATERIALS,
                summary=summary,
                payload=payload,
                deduplication_key=_build_deduplication_key(
                    kind=AutomaticReminderTaskKind.MISSING_MATERIALS,
                    member_id=member.member_id,
                    payload=payload,
                ),
            )
        )
    return candidates


def _build_unconfirmed_expense_candidates(
    *,
    task: ReimbursementTask,
    requested_by: str,
    invoices: list[InvoiceRecord],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
) -> list[AutomaticReminderTaskCreate]:
    items_by_member_id: dict[str, list[dict[str, Any]]] = {}
    for invoice in sorted(invoices, key=lambda item: (item.created_at, item.id)):
        for split in sorted(
            splits_by_invoice_id.get(invoice.id, []),
            key=lambda item: (item.updated_at, item.id),
        ):
            confirmation = confirmations_by_split_id.get(split.id)
            if confirmation is None:
                status = "missing"
            elif confirmation.status is ConfirmationStatus.CONFIRMED:
                continue
            elif confirmation.status is ConfirmationStatus.PENDING:
                status = "pending"
            else:
                status = "disputed"

            items_by_member_id.setdefault(split.member_id, []).append(
                {
                    "split_id": split.id,
                    "split_version": split.version,
                    "amount_cents": split.amount_cents,
                    "status": status,
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "confirmation_deadline": task.deadline.isoformat(),
                }
            )

    candidates: list[AutomaticReminderTaskCreate] = []
    for member_id in sorted(items_by_member_id):
        member_items = items_by_member_id[member_id]
        payload = {
            "split_ids": [item["split_id"] for item in member_items],
            "split_versions": [item["split_version"] for item in member_items],
            "statuses": [item["status"] for item in member_items],
            "invoice_ids": [item["invoice_id"] for item in member_items],
            "invoice_numbers": [item["invoice_number"] for item in member_items],
            "confirmation_deadline": task.deadline.isoformat(),
            "item_count": len(member_items),
        }
        summary = (
            "系统检测到未确认费用明细，请确认或处理异议："
            + "、".join(dict.fromkeys(payload["invoice_numbers"]))
        )
        candidates.append(
            AutomaticReminderTaskCreate(
                requested_by=requested_by,
                member_id=member_id,
                kind=AutomaticReminderTaskKind.UNCONFIRMED_EXPENSES,
                summary=summary,
                payload=payload,
                deduplication_key=_build_deduplication_key(
                    kind=AutomaticReminderTaskKind.UNCONFIRMED_EXPENSES,
                    member_id=member_id,
                    payload=payload,
                ),
            )
        )
    return candidates


def _build_deduplication_key(
    *,
    kind: AutomaticReminderTaskKind,
    member_id: str,
    payload: dict[str, Any],
) -> str:
    normalized = json.dumps(
        {
            "kind": kind.value,
            "member_id": member_id,
            "payload": payload,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(normalized.encode("utf-8")).hexdigest()


class InMemoryAutomaticReminderTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, AutomaticReminderTaskRecord] = {}
        self._lock = RLock()

    def create(
        self,
        *,
        task_id: str,
        data: AutomaticReminderTaskCreate,
    ) -> AutomaticReminderTaskRecord:
        now = datetime.now(timezone.utc)
        record = AutomaticReminderTaskRecord(
            id=str(uuid4()),
            task_id=task_id,
            member_id=data.member_id,
            requested_by=data.requested_by,
            kind=data.kind,
            status=AutomaticReminderTaskStatus.PENDING,
            summary=data.summary,
            payload=data.payload,
            deduplication_key=data.deduplication_key,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._tasks[record.id] = record
        return record

    def get_by_deduplication_key(
        self,
        *,
        task_id: str,
        deduplication_key: str,
    ) -> AutomaticReminderTaskRecord | None:
        with self._lock:
            for record in self._tasks.values():
                if (
                    record.task_id == task_id
                    and record.deduplication_key == deduplication_key
                ):
                    return record
        return None

    def list_by_task(self, task_id: str) -> list[AutomaticReminderTaskRecord]:
        with self._lock:
            records = [record for record in self._tasks.values() if record.task_id == task_id]
        return sorted(records, key=lambda record: (record.created_at, record.id))
