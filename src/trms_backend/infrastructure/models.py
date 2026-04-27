from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from trms_backend.infrastructure.database import Base


class GlobalInvoiceConfigRow(Base):
    __tablename__ = "global_invoice_configs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    invoice_title: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_number: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reimbursement_tasks.id"),
        nullable=True,
        index=True,
    )
    submitter_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    task_id_hint: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    submitter_id_hint: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    material_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    duplicate_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    claimed_by: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvoiceRow(Base):
    __tablename__ = "invoices"
    __table_args__ = (Index("ix_invoice_task_number", "task_id", "invoice_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reimbursement_tasks.id"),
        nullable=False,
        index=True,
    )
    material_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("materials.id"),
        nullable=False,
        index=True,
    )
    invoice_number: Mapped[str] = mapped_column(String(128), nullable=False)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    transaction_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_number: Mapped[str] = mapped_column(String(64), nullable=False)
    seller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    expense_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvoiceSupportingMaterialLinkRow(Base):
    __tablename__ = "invoice_supporting_material_links"
    __table_args__ = (
        Index(
            "ix_invoice_supporting_material_link_unique",
            "invoice_id",
            "material_id",
            unique=True,
        ),
        Index("ix_invoice_supporting_material_link_material", "material_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("invoices.id"),
        nullable=False,
        index=True,
    )
    material_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("materials.id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecognitionTaskRow(Base):
    __tablename__ = "recognition_tasks"
    __table_args__ = (Index("ix_recognition_task_material", "material_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    material_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("materials.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    is_final_fact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_response: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        JSON,
        nullable=True,
    )
    recognized_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ValidationResultRow(Base):
    __tablename__ = "validation_results"
    __table_args__ = (Index("ix_validation_target", "target_type", "target_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExpenseSplitRow(Base):
    __tablename__ = "expense_splits"
    __table_args__ = (Index("ix_expense_split_invoice_member", "invoice_id", "member_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("invoices.id"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConfirmationRow(Base):
    __tablename__ = "confirmations"
    __table_args__ = (Index("ix_confirmation_split_member", "split_id", "member_id", unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    split_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("expense_splits.id"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    dispute_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
