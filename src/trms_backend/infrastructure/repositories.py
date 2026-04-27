from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from trms_backend.domain.materials import (
    MaterialCreate,
    MaterialRecord,
    SubmissionChannel,
)
from trms_backend.domain.tasks import (
    ReimbursementTask,
    TaskCreate,
    TaskStatus,
)
from trms_backend.infrastructure.database import session_scope
from trms_backend.infrastructure.models import MaterialRow, TaskRow


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


class SqlAlchemyMaterialRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, data: MaterialCreate) -> MaterialRecord:
        with session_scope(self._session_factory) as session:
            duplicate_of = self._find_duplicate_material_id(session, data.task_id, data.sha256)
            row = MaterialRow(
                id=str(uuid4()),
                created_at=datetime.now(timezone.utc),
                duplicate_of=duplicate_of,
                **data.model_dump(mode="json"),
            )
            session.add(row)
        return _material_from_row(row)

    def list_by_task(self, task_id: str) -> list[MaterialRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(MaterialRow)
                .where(MaterialRow.task_id == task_id)
                .order_by(MaterialRow.created_at)
            ).all()
            return [_material_from_row(row) for row in rows]

    def _find_duplicate_material_id(self, session: Session, task_id: str, sha256: str) -> str | None:
        return session.scalar(
            select(MaterialRow.id)
            .where(MaterialRow.task_id == task_id, MaterialRow.sha256 == sha256)
            .order_by(MaterialRow.created_at)
            .limit(1)
        )


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


def _material_from_row(row: MaterialRow) -> MaterialRecord:
    return MaterialRecord(
        id=row.id,
        task_id=row.task_id,
        submitter_id=row.submitter_id,
        channel=SubmissionChannel(row.channel),
        original_filename=row.original_filename,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        duplicate_of=row.duplicate_of,
        created_at=row.created_at,
    )

