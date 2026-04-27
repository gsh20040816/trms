from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from trms_backend.infrastructure.database import Base


class TaskRow(Base):
    __tablename__ = "reimbursement_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    competition_name: Mapped[str] = mapped_column(String(255), nullable=False)
    competition_location: Mapped[str] = mapped_column(String(255), nullable=False)
    competition_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    competition_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    member_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    fee_categories: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    administrator_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    project_info: Mapped[str] = mapped_column(String(1024), nullable=False)
    reimburser_info: Mapped[str] = mapped_column(String(1024), nullable=False)
    invoice_title: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_number: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MaterialRow(Base):
    __tablename__ = "materials"
    __table_args__ = (Index("ix_material_task_sha256", "task_id", "sha256"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reimbursement_tasks.id"),
        nullable=False,
        index=True,
    )
    submitter_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    duplicate_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
