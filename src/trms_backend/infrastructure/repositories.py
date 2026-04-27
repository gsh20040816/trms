from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from trms_backend.domain.confirmations import (
    ConfirmationRecord,
    ConfirmationRepository,
    ConfirmationStatus,
    ConfirmationSubmit,
)
from trms_backend.domain.global_invoice_config import (
    GlobalInvoiceConfig,
    GlobalInvoiceConfigRepository,
)
from trms_backend.domain.invoices import (
    ExpenseType,
    InvoiceCreate,
    InvoiceRecord,
    InvoiceSupportingMaterialLinkRecord,
    ValidationRepository,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from trms_backend.domain.materials import (
    MaterialCreate,
    MaterialRecord,
    MaterialStatus,
    MaterialType,
    SubmissionChannel,
)
from trms_backend.domain.recognitions import (
    RecognitionFieldCorrectionRecord,
    RecognitionFailureDetail,
    RecognitionFieldResult,
    RecognitionRevalidationStatus,
    RecognitionTaskCreate,
    RecognitionTaskRecord,
    RecognitionTaskRepository,
    RecognitionResultPayload,
    RecognitionTaskStatus,
)
from trms_backend.domain.splits import ExpenseSplitItem, ExpenseSplitRecord, ExpenseSplitRepository
from trms_backend.domain.tasks import (
    ReimbursementTask,
    TaskCreate,
    TaskStatus,
)
from trms_backend.infrastructure.database import session_scope
from trms_backend.infrastructure.models import (
    ConfirmationRow,
    ExpenseSplitRow,
    GlobalInvoiceConfigRow,
    InvoiceRow,
    InvoiceSupportingMaterialLinkRow,
    MaterialRow,
    RecognitionTaskRow,
    TaskRow,
    ValidationResultRow,
)


class SqlAlchemyGlobalInvoiceConfigRepository(GlobalInvoiceConfigRepository):
    _default_id = "default"

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get(self) -> GlobalInvoiceConfig | None:
        with session_scope(self._session_factory) as session:
            row = session.get(GlobalInvoiceConfigRow, self._default_id)
            return _global_invoice_config_from_row(row) if row else None

    def set(self, config: GlobalInvoiceConfig) -> GlobalInvoiceConfig:
        now = datetime.now(timezone.utc)
        with session_scope(self._session_factory) as session:
            row = session.get(GlobalInvoiceConfigRow, self._default_id)
            if row is None:
                row = GlobalInvoiceConfigRow(
                    id=self._default_id,
                    created_at=now,
                    updated_at=now,
                    **config.model_dump(),
                )
            else:
                row.invoice_title = config.invoice_title
                row.tax_number = config.tax_number
                row.updated_at = now
            session.add(row)
        return _global_invoice_config_from_row(row)


class SqlAlchemyTaskRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, data: TaskCreate) -> ReimbursementTask:
        now = datetime.now(timezone.utc)
        row = TaskRow(
            id=str(uuid4()),
            status=TaskStatus.DRAFT.value,
            created_at=now,
            updated_at=now,
            **data.model_dump(),
        )
        with session_scope(self._session_factory) as session:
            session.add(row)
        return _task_from_row(row)

    def get(self, task_id: str) -> ReimbursementTask | None:
        with session_scope(self._session_factory) as session:
            row = session.get(TaskRow, task_id)
            return _task_from_row(row) if row else None

    def list(self) -> list[ReimbursementTask]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(select(TaskRow).order_by(TaskRow.created_at)).all()
            return [_task_from_row(row) for row in rows]

    def update_status(self, task_id: str, target_status: TaskStatus) -> ReimbursementTask | None:
        with session_scope(self._session_factory) as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return None
            row.status = target_status.value
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
        return _task_from_row(row)

    def update_member_ids(self, task_id: str, member_ids: list[str]) -> ReimbursementTask | None:
        with session_scope(self._session_factory) as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return None
            row.member_ids = member_ids
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
        return _task_from_row(row)


class SqlAlchemyMaterialRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, data: MaterialCreate) -> MaterialRecord:
        with session_scope(self._session_factory) as session:
            duplicate_of = self._find_duplicate_material_id(session, data)
            row = MaterialRow(
                id=str(uuid4()),
                created_at=datetime.now(timezone.utc),
                duplicate_of=duplicate_of,
                **data.model_dump(mode="json"),
            )
            session.add(row)
        return _material_from_row(row)

    def claim_pending_assignment(
        self,
        *,
        material_id: str,
        task_id: str,
        submitter_id: str,
        claimed_by: str,
    ) -> MaterialRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(MaterialRow, material_id)
            if row is None or row.status != MaterialStatus.PENDING_ASSIGNMENT.value:
                return None
            row.status = MaterialStatus.ASSIGNED.value
            row.task_id = task_id
            row.submitter_id = submitter_id
            row.duplicate_of = self._find_duplicate_material_id_for_assignment(
                session,
                task_id=task_id,
                sha256=row.sha256,
            )
            row.claimed_by = claimed_by
            row.claimed_at = datetime.now(timezone.utc)
            session.add(row)
        return _material_from_row(row)

    def list_by_task(self, task_id: str) -> list[MaterialRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(MaterialRow)
                .where(
                    MaterialRow.task_id == task_id,
                    MaterialRow.status == MaterialStatus.ASSIGNED.value,
                )
                .order_by(MaterialRow.created_at)
            ).all()
            return [_material_from_row(row) for row in rows]

    def get(self, material_id: str) -> MaterialRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(MaterialRow, material_id)
            return _material_from_row(row) if row else None

    def _find_duplicate_material_id(
        self,
        session: Session,
        data: MaterialCreate,
    ) -> str | None:
        if data.status is not MaterialStatus.ASSIGNED or data.task_id is None:
            return None
        return self._find_duplicate_material_id_for_assignment(
            session,
            task_id=data.task_id,
            sha256=data.sha256,
        )

    def _find_duplicate_material_id_for_assignment(
        self,
        session: Session,
        *,
        task_id: str,
        sha256: str,
    ) -> str | None:
        return session.scalar(
            select(MaterialRow.id)
            .where(
                MaterialRow.task_id == task_id,
                MaterialRow.status == MaterialStatus.ASSIGNED.value,
                MaterialRow.sha256 == sha256,
            )
            .order_by(MaterialRow.created_at)
            .limit(1)
        )


class SqlAlchemyInvoiceRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def upsert_for_material(
        self,
        task_id: str,
        material_id: str,
        data: InvoiceCreate,
    ) -> InvoiceRecord:
        now = datetime.now(timezone.utc)
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(InvoiceRow)
                .where(InvoiceRow.material_id == material_id)
                .order_by(InvoiceRow.created_at)
                .limit(1)
            )
            if row is None:
                row = InvoiceRow(
                    id=str(uuid4()),
                    task_id=task_id,
                    material_id=material_id,
                    created_at=now,
                    updated_at=now,
                    **data.model_dump(),
                )
            else:
                row.task_id = task_id
                row.invoice_number = data.invoice_number
                row.issue_date = data.issue_date
                row.transaction_time = data.transaction_time
                row.buyer_name = data.buyer_name
                row.tax_number = data.tax_number
                row.seller_name = data.seller_name
                row.amount_cents = data.amount_cents
                row.expense_type = data.expense_type.value
                row.updated_at = now
            session.add(row)
        return _invoice_from_row(row)

    def get(self, invoice_id: str) -> InvoiceRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(InvoiceRow, invoice_id)
            return _invoice_from_row(row) if row else None

    def list_by_task(self, task_id: str) -> list[InvoiceRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(InvoiceRow).where(InvoiceRow.task_id == task_id).order_by(InvoiceRow.created_at)
            ).all()
            return [_invoice_from_row(row) for row in rows]

    def attach_supporting_material(
        self,
        invoice_id: str,
        material_id: str,
    ) -> InvoiceSupportingMaterialLinkRecord:
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(InvoiceSupportingMaterialLinkRow).where(
                    InvoiceSupportingMaterialLinkRow.invoice_id == invoice_id,
                    InvoiceSupportingMaterialLinkRow.material_id == material_id,
                )
            )
            if row is None:
                row = InvoiceSupportingMaterialLinkRow(
                    id=str(uuid4()),
                    invoice_id=invoice_id,
                    material_id=material_id,
                    created_at=datetime.now(timezone.utc),
                )
            session.add(row)
        return _invoice_supporting_material_link_from_row(row)

    def detach_supporting_material(self, invoice_id: str, material_id: str) -> bool:
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(InvoiceSupportingMaterialLinkRow).where(
                    InvoiceSupportingMaterialLinkRow.invoice_id == invoice_id,
                    InvoiceSupportingMaterialLinkRow.material_id == material_id,
                )
            )
            if row is None:
                return False
            session.delete(row)
        return True

    def list_supporting_material_links(
        self,
        invoice_id: str,
    ) -> list[InvoiceSupportingMaterialLinkRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(InvoiceSupportingMaterialLinkRow)
                .where(InvoiceSupportingMaterialLinkRow.invoice_id == invoice_id)
                .order_by(InvoiceSupportingMaterialLinkRow.created_at)
            ).all()
            return [_invoice_supporting_material_link_from_row(row) for row in rows]

    def find_duplicate_invoice_id(
        self,
        task_id: str,
        invoice_number: str,
        exclude_invoice_id: str,
    ) -> str | None:
        with session_scope(self._session_factory) as session:
            return session.scalar(
                select(InvoiceRow.id)
                .where(
                    InvoiceRow.task_id == task_id,
                    InvoiceRow.invoice_number == invoice_number,
                    InvoiceRow.id != exclude_invoice_id,
                )
                .order_by(InvoiceRow.created_at)
                .limit(1)
            )


class SqlAlchemyValidationRepository(ValidationRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def replace_for_invoice(
        self,
        invoice_id: str,
        results: list[ValidationResult],
    ) -> list[ValidationResult]:
        with session_scope(self._session_factory) as session:
            session.execute(
                delete(ValidationResultRow).where(
                    ValidationResultRow.target_type == "invoice",
                    ValidationResultRow.target_id == invoice_id,
                )
            )
            for result in results:
                session.add(
                    ValidationResultRow(
                        id=result.id,
                        rule_code=result.rule_code,
                        target_type=result.target_type,
                        target_id=result.target_id,
                        severity=result.severity.value,
                        status=result.status.value,
                        message=result.message,
                        evidence=result.evidence,
                        created_at=result.created_at,
                    )
                )
        return results

    def list_by_invoice(self, invoice_id: str) -> list[ValidationResult]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(ValidationResultRow)
                .where(
                    ValidationResultRow.target_type == "invoice",
                    ValidationResultRow.target_id == invoice_id,
                )
                .order_by(ValidationResultRow.created_at)
            ).all()
            return [_validation_from_row(row) for row in rows]


class SqlAlchemyRecognitionTaskRepository(RecognitionTaskRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, data: RecognitionTaskCreate) -> RecognitionTaskRecord:
        now = datetime.now(timezone.utc)
        row = RecognitionTaskRow(
            id=str(uuid4()),
            status=RecognitionTaskStatus.PENDING.value,
            created_at=now,
            updated_at=now,
            **data.model_dump(),
        )
        with session_scope(self._session_factory) as session:
            session.add(row)
        return _recognition_task_from_row(row)

    def get(self, recognition_task_id: str) -> RecognitionTaskRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(RecognitionTaskRow, recognition_task_id)
            return _recognition_task_from_row(row) if row else None

    def get_latest_effective_by_material(self, material_id: str) -> RecognitionTaskRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(RecognitionTaskRow)
                .where(
                    RecognitionTaskRow.material_id == material_id,
                    RecognitionTaskRow.status != RecognitionTaskStatus.PENDING.value,
                )
                .order_by(RecognitionTaskRow.created_at.desc())
                .limit(1)
            )
            return _recognition_task_from_row(row) if row else None

    def list_by_material(self, material_id: str) -> list[RecognitionTaskRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(RecognitionTaskRow)
                .where(RecognitionTaskRow.material_id == material_id)
                .order_by(RecognitionTaskRow.created_at)
            ).all()
            return [_recognition_task_from_row(row) for row in rows]

    def update_status(
        self,
        recognition_task_id: str,
        target_status: RecognitionTaskStatus,
        result: RecognitionResultPayload | None = None,
        failure: RecognitionFailureDetail | None = None,
    ) -> RecognitionTaskRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(RecognitionTaskRow, recognition_task_id)
            if row is None:
                return None
            row.status = target_status.value
            row.failure_detail = failure.model_dump(mode="json") if failure is not None else None
            if result is not None:
                row.raw_response = result.raw_response
                row.recognized_fields = _recognized_fields_to_json(
                    result.recognized_fields,
                    default_updated_at=datetime.now(timezone.utc),
                )
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
        return _recognition_task_from_row(row)

    def apply_manual_corrections(
        self,
        *,
        material_id: str,
        actor_id: str,
        corrected_fields: dict[str, object],
        revalidation_field_names: set[str] | None = None,
    ) -> RecognitionTaskRecord:
        now = datetime.now(timezone.utc)
        tracked_revalidation_fields = revalidation_field_names or set()
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(RecognitionTaskRow)
                .where(RecognitionTaskRow.material_id == material_id)
                .order_by(RecognitionTaskRow.created_at.desc())
                .limit(1)
            )
            if row is None:
                row = RecognitionTaskRow(
                    id=str(uuid4()),
                    material_id=material_id,
                    status=RecognitionTaskStatus.NEEDS_CONFIRMATION.value,
                    is_final_fact=False,
                    created_at=now,
                    updated_at=now,
                )
            should_promote_pending_task = row.status == RecognitionTaskStatus.PENDING.value
            recognized_fields = {
                field_name: RecognitionFieldResult.model_validate(field_result)
                for field_name, field_result in (row.recognized_fields or {}).items()
            }
            manual_corrections = [
                RecognitionFieldCorrectionRecord.model_validate(item)
                for item in (row.manual_corrections or [])
            ]
            for field_name, corrected_value in corrected_fields.items():
                previous = recognized_fields.get(field_name)
                updated = RecognitionFieldResult(
                    value=corrected_value,
                    source="manual",
                    confidence=1,
                    status="recognized",
                    updated_at=now,
                )
                if _recognition_field_equals(previous, updated):
                    continue
                recognized_fields[field_name] = updated
                manual_corrections.append(
                    RecognitionFieldCorrectionRecord(
                        id=str(uuid4()),
                        field_name=field_name,
                        actor_id=actor_id,
                        before=previous,
                        after=updated,
                        revalidation_status=(
                            RecognitionRevalidationStatus.TRIGGERED
                            if field_name in tracked_revalidation_fields
                            else RecognitionRevalidationStatus.NOT_REQUIRED
                        ),
                        corrected_at=now,
                    )
                )
            if should_promote_pending_task and (recognized_fields or manual_corrections):
                row.status = RecognitionTaskStatus.NEEDS_CONFIRMATION.value
            row.recognized_fields = _recognized_fields_to_json(
                recognized_fields,
                default_updated_at=now,
            )
            row.manual_corrections = [item.model_dump(mode="json") for item in manual_corrections]
            row.updated_at = now
            session.add(row)
        return _recognition_task_from_row(row)


class SqlAlchemyExpenseSplitRepository(ExpenseSplitRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def replace_for_invoice(
        self,
        invoice_id: str,
        items: list[ExpenseSplitItem],
    ) -> list[ExpenseSplitRecord]:
        now = datetime.now(timezone.utc)
        rows = [
            ExpenseSplitRow(
                id=str(uuid4()),
                invoice_id=invoice_id,
                member_id=item.member_id,
                amount_cents=item.amount_cents,
                note=item.note,
                created_at=now,
                updated_at=now,
            )
            for item in items
        ]
        with session_scope(self._session_factory) as session:
            session.execute(delete(ExpenseSplitRow).where(ExpenseSplitRow.invoice_id == invoice_id))
            session.add_all(rows)
        return [_split_from_row(row) for row in rows]

    def list_by_invoice(self, invoice_id: str) -> list[ExpenseSplitRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(ExpenseSplitRow)
                .where(ExpenseSplitRow.invoice_id == invoice_id)
                .order_by(ExpenseSplitRow.created_at)
            ).all()
            return [_split_from_row(row) for row in rows]

    def get(self, split_id: str) -> ExpenseSplitRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(ExpenseSplitRow, split_id)
            return _split_from_row(row) if row else None


class SqlAlchemyConfirmationRepository(ConfirmationRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def upsert_for_split(
        self,
        split_id: str,
        payload: ConfirmationSubmit,
    ) -> ConfirmationRecord:
        now = datetime.now(timezone.utc)
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(ConfirmationRow).where(
                    ConfirmationRow.split_id == split_id,
                    ConfirmationRow.member_id == payload.member_id,
                )
            )
            if row is None:
                row = ConfirmationRow(
                    id=str(uuid4()),
                    split_id=split_id,
                    member_id=payload.member_id,
                    confirmed_at=now,
                    updated_at=now,
                    status=payload.status.value,
                    dispute_reason=payload.dispute_reason,
                )
            else:
                row.status = payload.status.value
                row.dispute_reason = payload.dispute_reason
                row.updated_at = now
            session.add(row)
        return _confirmation_from_row(row)

    def list_by_invoice(self, invoice_id: str) -> list[ConfirmationRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(ConfirmationRow)
                .join(ExpenseSplitRow, ConfirmationRow.split_id == ExpenseSplitRow.id)
                .where(ExpenseSplitRow.invoice_id == invoice_id)
                .order_by(ConfirmationRow.confirmed_at)
            ).all()
            return [_confirmation_from_row(row) for row in rows]


def _task_from_row(row: TaskRow) -> ReimbursementTask:
    return ReimbursementTask(
        id=row.id,
        status=TaskStatus(row.status),
        competition_name=row.competition_name,
        competition_location=row.competition_location,
        competition_start_date=row.competition_start_date,
        competition_end_date=row.competition_end_date,
        deadline=row.deadline,
        member_ids=list(row.member_ids),
        fee_categories=list(row.fee_categories),
        administrator_id=row.administrator_id,
        project_info=row.project_info,
        reimburser_info=row.reimburser_info,
        invoice_title=row.invoice_title,
        tax_number=row.tax_number,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _global_invoice_config_from_row(row: GlobalInvoiceConfigRow) -> GlobalInvoiceConfig:
    return GlobalInvoiceConfig(
        invoice_title=row.invoice_title,
        tax_number=row.tax_number,
    )


def _material_from_row(row: MaterialRow) -> MaterialRecord:
    return MaterialRecord(
        id=row.id,
        status=MaterialStatus(row.status),
        task_id=row.task_id,
        submitter_id=row.submitter_id,
        task_id_hint=row.task_id_hint,
        submitter_id_hint=row.submitter_id_hint,
        channel=SubmissionChannel(row.channel),
        material_type=MaterialType(row.material_type),
        storage_key=row.storage_key,
        original_filename=row.original_filename,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        duplicate_of=row.duplicate_of,
        claimed_by=row.claimed_by,
        claimed_at=row.claimed_at,
        created_at=row.created_at,
    )


def _invoice_from_row(row: InvoiceRow) -> InvoiceRecord:
    return InvoiceRecord(
        id=row.id,
        task_id=row.task_id,
        material_id=row.material_id,
        invoice_number=row.invoice_number,
        issue_date=row.issue_date,
        transaction_time=row.transaction_time,
        buyer_name=row.buyer_name,
        tax_number=row.tax_number,
        seller_name=row.seller_name,
        amount_cents=row.amount_cents,
        expense_type=ExpenseType(row.expense_type),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _invoice_supporting_material_link_from_row(
    row: InvoiceSupportingMaterialLinkRow,
) -> InvoiceSupportingMaterialLinkRecord:
    return InvoiceSupportingMaterialLinkRecord(
        id=row.id,
        invoice_id=row.invoice_id,
        material_id=row.material_id,
        created_at=row.created_at,
    )


def _validation_from_row(row: ValidationResultRow) -> ValidationResult:
    return ValidationResult(
        id=row.id,
        rule_code=row.rule_code,
        target_type=row.target_type,
        target_id=row.target_id,
        severity=ValidationSeverity(row.severity),
        status=ValidationStatus(row.status),
        message=row.message,
        evidence=row.evidence or {},
        created_at=row.created_at,
    )


def _recognition_task_from_row(row: RecognitionTaskRow) -> RecognitionTaskRecord:
    return RecognitionTaskRecord(
        id=row.id,
        material_id=row.material_id,
        status=RecognitionTaskStatus(row.status),
        is_final_fact=row.is_final_fact,
        failure=(
            RecognitionFailureDetail.model_validate(row.failure_detail)
            if row.failure_detail is not None
            else None
        ),
        raw_response=row.raw_response,
        recognized_fields={
            field_name: RecognitionFieldResult.model_validate(field_result)
            for field_name, field_result in (row.recognized_fields or {}).items()
        },
        manual_corrections=[
            RecognitionFieldCorrectionRecord.model_validate(item)
            for item in (row.manual_corrections or [])
        ],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _recognized_fields_to_json(
    recognized_fields: dict[str, RecognitionFieldResult],
    *,
    default_updated_at: datetime,
) -> dict[str, dict]:
    serialized: dict[str, dict] = {}
    for field_name, field_result in recognized_fields.items():
        normalized = field_result.model_copy(
            update={
                "updated_at": field_result.updated_at or default_updated_at,
            }
        )
        serialized[field_name] = normalized.model_dump(mode="json")
    return serialized


def _recognition_field_equals(
    previous: RecognitionFieldResult | None,
    updated: RecognitionFieldResult,
) -> bool:
    if previous is None:
        return False
    return (
        previous.value == updated.value
        and previous.source is updated.source
        and previous.confidence == updated.confidence
        and previous.status is updated.status
    )


def _split_from_row(row: ExpenseSplitRow) -> ExpenseSplitRecord:
    return ExpenseSplitRecord(
        id=row.id,
        invoice_id=row.invoice_id,
        member_id=row.member_id,
        amount_cents=row.amount_cents,
        note=row.note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _confirmation_from_row(row: ConfirmationRow) -> ConfirmationRecord:
    return ConfirmationRecord(
        id=row.id,
        split_id=row.split_id,
        member_id=row.member_id,
        status=ConfirmationStatus(row.status),
        dispute_reason=row.dispute_reason,
        confirmed_at=row.confirmed_at,
        updated_at=row.updated_at,
    )
