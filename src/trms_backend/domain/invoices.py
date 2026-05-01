from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field, model_validator


class ExpenseType(StrEnum):
    REGISTRATION = "registration"
    RAILWAY = "railway"
    AIRFARE = "airfare"
    LOCAL_TRANSPORT = "local_transport"
    HOTEL = "hotel"
    OTHER = "other"


class InvoiceMemberSubmissionStatus(StrEnum):
    UNSUBMITTED = "unsubmitted"
    SUBMITTED = "submitted"


class ValidationSeverity(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


class ValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    NOT_APPLICABLE = "not_applicable"


class InvoiceCreate(BaseModel):
    invoice_number: str = Field(min_length=1)
    issue_date: date | None = None
    transaction_time: datetime | None = None
    buyer_name: str = Field(min_length=1)
    tax_number: str = Field(min_length=1)
    seller_name: str | None = None
    corporate_transfer_reference: str | None = None
    is_paper_invoice: bool = False
    paper_invoice_received: bool = False
    paper_invoice_received_at: datetime | None = None
    paper_invoice_received_by: str | None = None
    amount_cents: int = Field(gt=0)
    expense_type: ExpenseType

    @model_validator(mode="after")
    def normalize_text(self) -> InvoiceCreate:
        self.invoice_number = self.invoice_number.strip()
        self.buyer_name = self.buyer_name.strip()
        self.tax_number = self.tax_number.strip()
        if self.seller_name is not None:
            self.seller_name = self.seller_name.strip() or None
        if self.corporate_transfer_reference is not None:
            self.corporate_transfer_reference = self.corporate_transfer_reference.strip() or None
        if self.paper_invoice_received_by is not None:
            self.paper_invoice_received_by = self.paper_invoice_received_by.strip() or None
        return self


class ManualInvoiceEntry(BaseModel):
    actor_id: str = Field(min_length=1)
    invoice_number: str = Field(min_length=1)
    issue_date: date | None = None
    transaction_time: datetime | None = None
    buyer_name: str = Field(min_length=1)
    tax_number: str = Field(min_length=1)
    seller_name: str | None = None
    corporate_transfer_reference: str | None = None
    is_paper_invoice: bool = False
    amount_cents: int = Field(gt=0)
    expense_type: ExpenseType

    @model_validator(mode="after")
    def normalize_text(self) -> ManualInvoiceEntry:
        self.actor_id = self.actor_id.strip()
        self.invoice_number = self.invoice_number.strip()
        self.buyer_name = self.buyer_name.strip()
        self.tax_number = self.tax_number.strip()
        if self.seller_name is not None:
            self.seller_name = self.seller_name.strip() or None
        if self.corporate_transfer_reference is not None:
            self.corporate_transfer_reference = self.corporate_transfer_reference.strip() or None
        return self

    def to_invoice_create(self) -> InvoiceCreate:
        return InvoiceCreate.model_validate(
            self.model_dump(exclude={"actor_id"})
            | {
                "paper_invoice_received": False,
                "paper_invoice_received_at": None,
                "paper_invoice_received_by": None,
            }
        )


class InvoiceRecord(BaseModel):
    id: str
    task_id: str
    material_id: str
    invoice_number: str
    issue_date: date | None
    transaction_time: datetime | None
    buyer_name: str
    tax_number: str
    seller_name: str | None
    corporate_transfer_reference: str | None = None
    is_paper_invoice: bool = False
    paper_invoice_received: bool = False
    paper_invoice_received_at: datetime | None = None
    paper_invoice_received_by: str | None = None
    amount_cents: int
    expense_type: ExpenseType
    member_submission_status: InvoiceMemberSubmissionStatus = InvoiceMemberSubmissionStatus.UNSUBMITTED
    submitted_by_member_id: str | None = None
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceSupportingMaterialLinkRecord(BaseModel):
    id: str
    invoice_id: str
    material_id: str
    created_at: datetime


class ValidationResult(BaseModel):
    id: str
    rule_code: str
    target_type: str
    target_id: str
    severity: ValidationSeverity
    status: ValidationStatus
    message: str
    evidence: dict[str, Any]
    created_at: datetime


class InvoiceRepository(Protocol):
    def upsert_for_material(
        self,
        task_id: str,
        material_id: str,
        data: InvoiceCreate,
    ) -> InvoiceRecord:
        raise NotImplementedError

    def get(self, invoice_id: str) -> InvoiceRecord | None:
        raise NotImplementedError

    def get_by_material(self, material_id: str) -> InvoiceRecord | None:
        raise NotImplementedError

    def list_by_task(self, task_id: str) -> list[InvoiceRecord]:
        raise NotImplementedError

    def list_by_supporting_material(self, material_id: str) -> list[InvoiceRecord]:
        raise NotImplementedError

    def attach_supporting_material(
        self,
        invoice_id: str,
        material_id: str,
    ) -> InvoiceSupportingMaterialLinkRecord:
        raise NotImplementedError

    def detach_supporting_material(self, invoice_id: str, material_id: str) -> bool:
        raise NotImplementedError

    def list_supporting_material_links(
        self,
        invoice_id: str,
    ) -> list[InvoiceSupportingMaterialLinkRecord]:
        raise NotImplementedError

    def find_duplicate_invoice_id(
        self,
        task_id: str,
        invoice_number: str,
        exclude_invoice_id: str,
    ) -> str | None:
        raise NotImplementedError

    def update_member_submission_status(
        self,
        *,
        invoice_id: str,
        status: InvoiceMemberSubmissionStatus,
        submitted_by_member_id: str | None,
        submitted_at: datetime | None,
    ) -> InvoiceRecord | None:
        raise NotImplementedError

    def confirm_paper_invoice_received(
        self,
        *,
        invoice_id: str,
        received_by: str,
        received_at: datetime,
    ) -> InvoiceRecord | None:
        raise NotImplementedError


class ValidationRepository(Protocol):
    def replace_for_invoice(
        self,
        invoice_id: str,
        results: list[ValidationResult],
    ) -> list[ValidationResult]:
        raise NotImplementedError

    def list_by_invoice(self, invoice_id: str) -> list[ValidationResult]:
        raise NotImplementedError


class InvoiceManualEntryActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "only the material submitter or task administrator can record invoice fields"
        )


def ensure_manual_invoice_entry_actor_allowed(
    *,
    actor_id: str,
    submitter_id: str | None,
    administrator_id: str,
) -> None:
    if actor_id == administrator_id:
        return
    if submitter_id is not None and actor_id == submitter_id:
        return
    raise InvoiceManualEntryActorNotAllowedError()
