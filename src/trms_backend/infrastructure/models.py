from datetime import date, datetime

from sqlalchemy import BigInteger, JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from trms_backend.infrastructure.database import Base


class GlobalInvoiceConfigRow(Base):
    __tablename__ = "global_invoice_configs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    invoice_title: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_number: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SystemAiProviderConfigRow(Base):
    __tablename__ = "system_ai_provider_configs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    text_llm_base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text_llm_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text_llm_timeout_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_llm_max_retries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_llm_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    vlm_base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vlm_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vlm_timeout_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    vlm_max_retries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vlm_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegistrationPolicyRow(Base):
    __tablename__ = "registration_policies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    allowed_email_hosts: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserAccountRow(Base):
    __tablename__ = "user_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    roles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    member_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    registration_source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthSessionRow(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_accounts.id"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    active_role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TaskRow(Base):
    __tablename__ = "reimbursement_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    competition_name: Mapped[str] = mapped_column(String(255), nullable=False)
    competition_location: Mapped[str] = mapped_column(String(255), nullable=False)
    competition_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    competition_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    email_submission_key: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        unique=True,
        index=True,
    )
    member_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    fee_categories: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    administrator_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
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


class TelegramAccountBindingRow(Base):
    __tablename__ = "telegram_account_bindings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    member_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TelegramBindingAuthorizationRow(Base):
    __tablename__ = "telegram_binding_authorizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TelegramTaskContextRow(Base):
    __tablename__ = "telegram_task_contexts"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reimbursement_tasks.id"),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EmailAccountBindingRow(Base):
    __tablename__ = "email_account_bindings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    member_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EmailBindingVerificationRow(Base):
    __tablename__ = "email_binding_verifications"
    __table_args__ = (
        Index("ix_email_binding_verification_member_email", "member_id", "email", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    member_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegistrationEmailVerificationRow(Base):
    __tablename__ = "registration_email_verifications"
    __table_args__ = (
        Index("ix_registration_email_verification_email", "email", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EmailInboxRecordRow(Base):
    __tablename__ = "email_inbox_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mailbox_uid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    sender_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    raw_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    result_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_member_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    submitted_task_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    resolved_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
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
    corporate_transfer_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_paper_invoice: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paper_invoice_received: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paper_invoice_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paper_invoice_received_by: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    expense_type: Mapped[str] = mapped_column(String(64), nullable=False)
    member_submission_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unsubmitted",
        index=True,
    )
    submitted_by_member_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    failure_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_response: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        JSON,
        nullable=True,
    )
    recognized_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    manual_corrections: Mapped[list | None] = mapped_column(JSON, nullable=True)
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
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
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
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConfirmationRow(Base):
    __tablename__ = "confirmations"
    __table_args__ = (
        Index(
            "ix_confirmation_split_member_version",
            "split_id",
            "member_id",
            "split_version",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    split_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("expense_splits.id"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    split_version: Mapped[int] = mapped_column(Integer, nullable=False)
    split_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    split_note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    dispute_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MaterialReminderRow(Base):
    __tablename__ = "material_reminders"
    __table_args__ = (
        Index("ix_material_reminder_task_created_at", "task_id", "created_at"),
        Index("ix_material_reminder_task_member", "task_id", "member_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reimbursement_tasks.id"),
        nullable=False,
        index=True,
    )
    administrator_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    member_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AutomaticReminderTaskRow(Base):
    __tablename__ = "automatic_reminder_tasks"
    __table_args__ = (
        Index("ix_automatic_reminder_task_created_at", "task_id", "created_at"),
        Index("ix_automatic_reminder_task_member_kind", "task_id", "member_id", "kind"),
        Index(
            "ix_automatic_reminder_task_deduplication",
            "task_id",
            "deduplication_key",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reimbursement_tasks.id"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    deduplication_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExportJobRow(Base):
    __tablename__ = "export_jobs"
    __table_args__ = (
        Index("ix_export_job_task_created_at", "task_id", "created_at"),
        Index("ix_export_job_task_status", "task_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reimbursement_tasks.id"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLogRow(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_log_actor_created_at", "actor_id", "created_at"),
        Index("ix_audit_log_object_created_at", "object_type", "object_id", "created_at"),
        Index("ix_audit_log_task_created_at", "task_id", "created_at"),
        Index("ix_audit_log_request_id", "request_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String(1024), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False)
    task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("reimbursement_tasks.id"),
        nullable=True,
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
