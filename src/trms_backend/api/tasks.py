from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, model_validator

from trms_backend.api.error_responses import ensure_request_id
from trms_backend.api.request_identity import (
    RequestIdentity,
    build_authenticated_request_identity_dependency,
)
from trms_backend.api.request_identity_http import resolve_required_actor_request_field
from trms_backend.api.request_task_access import TaskAccessScope, resolve_task_access_scope
from trms_backend.application.expense_audit import record_split_confirmation_audit
from trms_backend.application.invoice_member_submission import (
    InvoiceMemberSubmissionService,
)
from trms_backend.application.invoice_member_submission_withdrawal import (
    InvoiceMemberSubmissionWithdrawalService,
)
from trms_backend.domain.automatic_reminders import (
    AutomaticReminderTaskActorNotAllowedError,
    AutomaticReminderTaskGenerate,
    AutomaticReminderTaskRepository,
    generate_task_automatic_reminder_tasks,
    list_task_automatic_reminder_tasks,
)
from trms_backend.domain.audit_logs import AuditLogRepository
from trms_backend.domain.auth import AuthRepository, UserRole
from trms_backend.domain.confirmations import (
    ConfirmationDisputeResolve,
    ConfirmationRepository,
    ConfirmationStatus,
    ConfirmationSubmit,
)
from trms_backend.domain.expense_details import (
    ExpenseDetailActorNotAllowedError,
    build_expense_detail_list,
)
from trms_backend.domain.expense_disputes import (
    ExpenseDisputeActorNotAllowedError,
    build_expense_dispute_list,
    ensure_task_administrator,
)
from trms_backend.domain.overdue_confirmations import (
    OverdueConfirmationActorNotAllowedError,
    build_overdue_confirmation_list,
)
from trms_backend.domain.global_invoice_config import GlobalInvoiceConfigRepository
from trms_backend.domain.invoices import InvoiceRepository, ValidationRepository
from trms_backend.domain.material_reminders import (
    MaterialReminderCreate,
    MaterialReminderRepository,
    TaskMaterialReminderActorNotAllowedError,
    create_task_material_reminder,
    list_task_material_reminders,
)
from trms_backend.domain.materials import MaterialRecord, MaterialRepository
from trms_backend.domain.missing_materials import (
    TaskMissingMaterialActorNotAllowedError,
    build_visible_missing_material_list,
)
from trms_backend.domain.recognitions import RecognitionTaskRepository
from trms_backend.domain.splits import ExpenseSplitRepository
from trms_backend.domain.task_review_summary import (
    TaskReviewSummaryActorNotAllowedError,
    build_task_review_summary,
)
from trms_backend.domain.task_readiness import (
    TaskReadinessActorNotAllowedError,
    build_task_readiness_summary,
)
from trms_backend.domain.task_member_status import (
    TaskMemberStatusActorNotAllowedError,
    build_task_member_status_report,
)
from trms_backend.domain.task_member_workbench import (
    TaskMemberWorkbenchActorNotAllowedError,
    build_task_member_workbench_summary,
)
from trms_backend.domain.task_shared_invoices import (
    TaskSharedInvoiceActorNotAllowedError,
    build_task_shared_invoice_report,
)
from trms_backend.domain.task_supporting_material_linkage import (
    build_task_supporting_material_linkage_report,
)
from trms_backend.domain.tasks import (
    TaskCreateInput,
    TaskCompletionValidationError,
    MissingTaskInvoiceConfigError,
    ReimbursementTask,
    TaskMembersUpdate,
    TaskRepository,
    TaskPublishValidationError,
    TaskReviewValidationError,
    TaskStatus,
    TaskStatusUpdate,
    TaskUpdateInput,
    build_task_member_summaries,
    can_transition,
    close_expired_open_tasks,
    ensure_task_can_enter_ready_to_export,
    ensure_task_can_publish,
    resolve_task_create,
)


class TaskMaterialReminderCreateRequest(BaseModel):
    administrator_id: str | None = None
    member_id: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def normalize_text(self) -> "TaskMaterialReminderCreateRequest":
        if self.administrator_id is not None:
            self.administrator_id = self.administrator_id.strip() or None
        self.member_id = self.member_id.strip()
        self.content = self.content.strip()
        return self

    def to_domain(self, *, administrator_id: str) -> MaterialReminderCreate:
        return MaterialReminderCreate(
            administrator_id=administrator_id,
            member_id=self.member_id,
            content=self.content,
        )


class InvoiceMemberSubmissionBatchRequest(BaseModel):
    actor_id: str | None = None
    invoice_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_fields(self) -> "InvoiceMemberSubmissionBatchRequest":
        if self.actor_id is not None:
            self.actor_id = self.actor_id.strip() or None
        self.invoice_ids = [invoice_id.strip() for invoice_id in self.invoice_ids if invoice_id.strip()]
        if not self.invoice_ids:
            raise ValueError("invoice_ids must not be empty")
        return self


def build_task_router(
    auth_repository: AuthRepository,
    repository: TaskRepository,
    global_invoice_config_repository: GlobalInvoiceConfigRepository,
    material_reminder_repository: MaterialReminderRepository,
    automatic_reminder_task_repository: AutomaticReminderTaskRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    validation_repository: ValidationRepository,
    recognition_task_repository: RecognitionTaskRepository,
    split_repository: ExpenseSplitRepository,
    confirmation_repository: ConfirmationRepository,
    audit_log_repository: AuditLogRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/tasks", tags=["tasks"])
    authenticated_request_identity = build_authenticated_request_identity_dependency(
        auth_repository
    )
    invoice_member_submission_service = InvoiceMemberSubmissionService(
        material_repository=material_repository,
        invoice_repository=invoice_repository,
        audit_log_repository=audit_log_repository,
    )
    invoice_member_submission_withdrawal_service = InvoiceMemberSubmissionWithdrawalService(
        material_repository=material_repository,
        invoice_repository=invoice_repository,
        audit_log_repository=audit_log_repository,
    )

    def enrich_task_member_summaries(task: ReimbursementTask) -> ReimbursementTask:
        users = auth_repository.list_users_by_member_identifiers(task.member_ids)
        return task.model_copy(
            update={
                "member_summaries": build_task_member_summaries(task.member_ids, users),
            }
        )

    def ensure_task_management_role(
        identity: RequestIdentity,
        *,
        forbidden_detail: str,
    ) -> None:
        if identity.role not in {UserRole.ADMIN, UserRole.SYSTEM_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=forbidden_detail,
            )

    @router.post("", status_code=status.HTTP_201_CREATED)
    def create_task(
        payload: TaskCreateInput,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        ensure_task_management_role(
            identity,
            forbidden_detail="actor is not allowed to create reimbursement tasks",
        )
        resolve_required_actor_request_field(
            identity,
            payload.administrator_id,
            field_name="administrator_id",
        )
        try:
            task_create = resolve_task_create(payload, global_invoice_config_repository.get())
        except MissingTaskInvoiceConfigError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        return enrich_task_member_summaries(repository.create(task_create))

    @router.get("")
    def list_tasks(
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        member_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        if identity.is_authenticated and identity.role is UserRole.MEMBER:
            resolved_member_id = resolve_required_actor_request_field(
                identity,
                member_id,
                field_name="member_id",
            )
            return [enrich_task_member_summaries(task) for task in repository.list_for_member(resolved_member_id)]
        if identity.is_authenticated and identity.actor_id is not None:
            return [
                enrich_task_member_summaries(task)
                for task in repository.list()
                if task.administrator_id == identity.actor_id
            ]
        return []

    @router.get("/{task_id}")
    def get_task(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to view this task",
        )
        return enrich_task_member_summaries(task)

    @router.get("/{task_id}/members")
    def get_task_members(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to view task members for this task",
        )
        return {"items": enrich_task_member_summaries(task).member_summaries}

    @router.post("/{task_id}/automatic-reminder-tasks", status_code=status.HTTP_201_CREATED)
    def generate_automatic_reminder_tasks(
        task_id: str,
        payload: AutomaticReminderTaskGenerate,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        materials = material_repository.list_by_task(task_id)
        invoices = invoice_repository.list_by_task(task_id)
        validations_by_invoice_id = {
            invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation

        try:
            return generate_task_automatic_reminder_tasks(
                task,
                payload=AutomaticReminderTaskGenerate(
                    actor_id=resolve_required_actor_request_field(
                        identity,
                        payload.actor_id,
                        field_name="actor_id",
                    )
                ),
                repository=automatic_reminder_task_repository,
                materials=materials,
                invoices=invoices,
                validations_by_invoice_id=validations_by_invoice_id,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
            )
        except AutomaticReminderTaskActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/automatic-reminder-tasks")
    def list_automatic_reminder_tasks(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        try:
            return {
                "items": list_task_automatic_reminder_tasks(
                    task,
                    actor_id=resolve_required_actor_request_field(
                        identity,
                        actor_id,
                        field_name="actor_id",
                    ),
                    repository=automatic_reminder_task_repository,
                )
            }
        except AutomaticReminderTaskActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.post("/{task_id}/material-reminders", status_code=status.HTTP_201_CREATED)
    def create_material_reminder(
        task_id: str,
        payload: TaskMaterialReminderCreateRequest,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        administrator_id = resolve_required_actor_request_field(
            identity,
            payload.administrator_id,
            field_name="administrator_id",
        )
        try:
            return create_task_material_reminder(
                task,
                reminder_repository=material_reminder_repository,
                payload=payload.to_domain(administrator_id=administrator_id),
            )
        except TaskMaterialReminderActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/material-reminders")
    def list_material_reminders(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            return {
                "items": list_task_material_reminders(
                    task,
                    reminder_repository=material_reminder_repository,
                    actor_id=resolved_actor_id,
                )
            }
        except TaskMaterialReminderActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/expense-details")
    def list_task_expense_details(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoices = invoice_repository.list_by_task(task_id)
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            return build_expense_detail_list(
                task,
                actor_id=resolved_actor_id,
                invoices=invoices,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
            )
        except ExpenseDetailActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/member-status")
    def get_task_member_status(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )

        materials = material_repository.list_by_task(task_id)
        invoices = invoice_repository.list_by_task(task_id)
        validations_by_invoice_id = {
            invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        latest_recognitions_by_material_id = {}
        for material in materials:
            if material.submitter_id != resolved_actor_id:
                continue
            latest_recognitions_by_material_id[material.id] = (
                recognition_task_repository.get_latest_effective_by_material(material.id)
            )
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation

        try:
            return build_task_member_status_report(
                task,
                actor_id=resolved_actor_id,
                materials=materials,
                invoices=invoices,
                latest_recognitions_by_material_id=latest_recognitions_by_material_id,
                validations_by_invoice_id=validations_by_invoice_id,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
            )
        except TaskMemberStatusActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/member-workbench")
    def get_task_member_workbench(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )

        materials = material_repository.list_by_task(task_id)
        invoices = invoice_repository.list_by_task(task_id)
        validations_by_invoice_id = {
            invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        latest_recognitions_by_material_id = {}
        for material in materials:
            if material.submitter_id != resolved_actor_id:
                continue
            latest_recognitions_by_material_id[material.id] = (
                recognition_task_repository.get_latest_effective_by_material(material.id)
            )
        supporting_materials_by_invoice_id: dict[str, list[MaterialRecord]] = {}
        shared_supporting_materials_by_invoice_id: dict[str, list[MaterialRecord]] = {}
        linked_invoice_ids_by_material_id: dict[str, list[str]] = {
            material.id: []
            for material in materials
        }
        for invoice in invoices:
            supporting_materials: list[MaterialRecord] = []
            shared_supporting_materials: list[MaterialRecord] = []
            for link in invoice_repository.list_supporting_material_links(invoice.id):
                linked_invoice_ids_by_material_id.setdefault(link.material_id, []).append(invoice.id)
                material = material_repository.get(link.material_id)
                if material is None:
                    continue
                shared_supporting_materials.append(material)
                if material.submitter_id != resolved_actor_id:
                    continue
                supporting_materials.append(material)
            supporting_materials_by_invoice_id[invoice.id] = supporting_materials
            shared_supporting_materials_by_invoice_id[invoice.id] = shared_supporting_materials
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_invoice_id = {
            invoice.id: confirmation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        current_confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                current_confirmations_by_split_id[confirmation.split_id] = confirmation

        try:
            return build_task_member_workbench_summary(
                task,
                actor_id=resolved_actor_id,
                materials=materials,
                invoices=invoices,
                latest_recognitions_by_material_id=latest_recognitions_by_material_id,
                validations_by_invoice_id=validations_by_invoice_id,
                supporting_materials_by_invoice_id=supporting_materials_by_invoice_id,
                shared_supporting_materials_by_invoice_id=shared_supporting_materials_by_invoice_id,
                linked_invoice_ids_by_material_id=linked_invoice_ids_by_material_id,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_invoice_id=confirmations_by_invoice_id,
                current_confirmations_by_split_id=current_confirmations_by_split_id,
            )
        except TaskMemberWorkbenchActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/shared-invoices")
    def get_task_shared_invoices(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        invoices = invoice_repository.list_by_task(task_id)
        materials_by_id = {
            material.id: material for material in material_repository.list_by_task(task_id)
        }
        supporting_materials_by_invoice_id: dict[str, list[MaterialRecord]] = {}
        for invoice in invoices:
            supporting_materials = []
            for link in invoice_repository.list_supporting_material_links(invoice.id):
                material = material_repository.get(link.material_id)
                if material is not None:
                    supporting_materials.append(material)
            supporting_materials_by_invoice_id[invoice.id] = supporting_materials
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        validations_by_invoice_id = {
            invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }

        try:
            return build_task_shared_invoice_report(
                task,
                actor_id=resolved_actor_id,
                invoices=invoices,
                materials_by_id=materials_by_id,
                validations_by_invoice_id=validations_by_invoice_id,
                supporting_materials_by_invoice_id=supporting_materials_by_invoice_id,
                splits_by_invoice_id=splits_by_invoice_id,
            )
        except TaskSharedInvoiceActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.post("/{task_id}/invoice-submissions")
    def submit_task_invoices(
        task_id: str,
        request: Request,
        payload: InvoiceMemberSubmissionBatchRequest,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            payload.actor_id,
            field_name="actor_id",
        )
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to submit invoices for this task",
        )
        if scope is not TaskAccessScope.MEMBER or identity.role is not UserRole.MEMBER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="actor is not allowed to submit invoices for this task",
            )

        invoices = invoice_repository.list_by_task(task_id)
        validations_by_invoice_id = {
            invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation

        result = invoice_member_submission_service.submit_batch(
            task=task,
            actor_id=resolved_actor_id,
            actor_role=identity.role,
            invoice_ids=payload.invoice_ids,
            validations_by_invoice_id=validations_by_invoice_id,
            splits_by_invoice_id=splits_by_invoice_id,
            confirmations_by_split_id=confirmations_by_split_id,
            request_id=ensure_request_id(request),
        )
        return {
            "status": result.status,
            "items": result.items,
            "failures": result.failures,
        }

    @router.post("/{task_id}/invoice-submission-withdrawals")
    def withdraw_task_invoice_submissions(
        task_id: str,
        request: Request,
        payload: InvoiceMemberSubmissionBatchRequest,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            payload.actor_id,
            field_name="actor_id",
        )
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to withdraw invoice submissions for this task",
        )
        if scope is not TaskAccessScope.MEMBER or identity.role is not UserRole.MEMBER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="actor is not allowed to withdraw invoice submissions for this task",
            )

        result = invoice_member_submission_withdrawal_service.withdraw_batch(
            task=task,
            actor_id=resolved_actor_id,
            actor_role=identity.role,
            invoice_ids=payload.invoice_ids,
            request_id=ensure_request_id(request),
        )
        return {
            "status": result.status,
            "items": result.items,
            "failures": result.failures,
        }

    @router.get("/{task_id}/supporting-material-linkage")
    def get_task_supporting_material_linkage(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        scope = resolve_task_access_scope(
            identity,
            task,
            forbidden_detail="actor is not allowed to view supporting material linkage for this task",
        )
        materials = material_repository.list_by_task(task_id)
        materials_by_id = {material.id: material for material in materials}
        invoices = invoice_repository.list_by_task(task_id)
        linked_invoice_ids_by_material_id: dict[str, list[str]] = {}
        for material in materials:
            linked_invoice_ids_by_material_id[material.id] = [
                invoice.id
                for invoice in invoice_repository.list_by_supporting_material(material.id)
            ]

        return build_task_supporting_material_linkage_report(
            task,
            actor_id=resolved_actor_id,
            include_all_members=scope is TaskAccessScope.ADMINISTRATOR,
            materials=materials,
            invoices=invoices,
            materials_by_id=materials_by_id,
            linked_invoice_ids_by_material_id=linked_invoice_ids_by_material_id,
        )

    @router.get("/{task_id}/missing-materials")
    def list_task_missing_materials(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoices = invoice_repository.list_by_task(task_id)
        materials_by_id = {
            material.id: material for material in material_repository.list_by_task(task_id)
        }
        validations_by_invoice_id = {
            invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
        }

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            return build_visible_missing_material_list(
                task,
                actor_id=resolved_actor_id,
                invoices=invoices,
                materials_by_id=materials_by_id,
                validations_by_invoice_id=validations_by_invoice_id,
            )
        except TaskMissingMaterialActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/expense-disputes")
    def list_task_expense_disputes(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoices = invoice_repository.list_by_task(task_id)
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation

        try:
            return build_expense_dispute_list(
                task,
                administrator_id=resolve_required_actor_request_field(
                    identity,
                    actor_id,
                    field_name="actor_id",
                ),
                invoices=invoices,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
            )
        except ExpenseDisputeActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/overdue-confirmations")
    def list_task_overdue_confirmations(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        invoices = invoice_repository.list_by_task(task_id)
        splits_by_invoice_id = {
            invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
        }
        confirmations_by_split_id = {}
        for invoice in invoices:
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            return build_overdue_confirmation_list(
                task,
                administrator_id=resolved_actor_id,
                invoices=invoices,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
            )
        except OverdueConfirmationActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/review-summary")
    def get_task_review_summary(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        materials = material_repository.list_by_task(task_id)
        pending_assignment_materials = material_repository.list_pending_assignment_by_task_hint(task_id)
        latest_recognitions_by_material_id = {}
        for material in materials:
            recognition_tasks = recognition_task_repository.list_by_material(material.id)
            latest_recognitions_by_material_id[material.id] = (
                recognition_tasks[-1] if recognition_tasks else None
            )

        invoices = invoice_repository.list_by_task(task_id)
        invoice_by_material_id = {invoice.material_id: invoice for invoice in invoices}
        supporting_invoice_ids_by_material_id: dict[str, list[str]] = {}
        supporting_material_ids_by_invoice_id: dict[str, list[str]] = {}
        validations_by_invoice_id = {}
        splits_by_invoice_id = {}
        confirmations_by_split_id = {}
        for invoice in invoices:
            supporting_links = invoice_repository.list_supporting_material_links(invoice.id)
            supporting_material_ids = [link.material_id for link in supporting_links]
            supporting_material_ids_by_invoice_id[invoice.id] = supporting_material_ids
            for material_id in supporting_material_ids:
                supporting_invoice_ids_by_material_id.setdefault(material_id, []).append(invoice.id)

            validations_by_invoice_id[invoice.id] = validation_repository.list_by_invoice(invoice.id)
            splits_by_invoice_id[invoice.id] = split_repository.list_by_invoice(invoice.id)
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            return build_task_review_summary(
                task,
                administrator_id=resolved_actor_id,
                materials=materials,
                pending_assignment_materials=pending_assignment_materials,
                latest_recognitions_by_material_id=latest_recognitions_by_material_id,
                invoices=invoices,
                invoice_by_material_id=invoice_by_material_id,
                supporting_invoice_ids_by_material_id=supporting_invoice_ids_by_material_id,
                supporting_material_ids_by_invoice_id=supporting_material_ids_by_invoice_id,
                validations_by_invoice_id=validations_by_invoice_id,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
            )
        except TaskReviewSummaryActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/readiness")
    def get_task_readiness(
        task_id: str,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        actor_id: Annotated[str | None, Query(min_length=1)] = None,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        materials = material_repository.list_by_task(task_id)
        pending_assignment_materials = material_repository.list_pending_assignment_by_task_hint(task_id)
        latest_recognitions_by_material_id = {}
        for material in materials:
            recognition_tasks = recognition_task_repository.list_by_material(material.id)
            latest_recognitions_by_material_id[material.id] = (
                recognition_tasks[-1] if recognition_tasks else None
            )

        invoices = invoice_repository.list_by_task(task_id)
        validations_by_invoice_id = {}
        splits_by_invoice_id = {}
        confirmations_by_split_id = {}
        linked_invoice_ids_by_material_id: dict[str, list[str]] = {
            material.id: []
            for material in materials
        }
        for invoice in invoices:
            supporting_links = invoice_repository.list_supporting_material_links(invoice.id)
            for link in supporting_links:
                linked_invoice_ids_by_material_id.setdefault(link.material_id, []).append(invoice.id)
            validations_by_invoice_id[invoice.id] = validation_repository.list_by_invoice(invoice.id)
            splits_by_invoice_id[invoice.id] = split_repository.list_by_invoice(invoice.id)
            for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                confirmations_by_split_id[confirmation.split_id] = confirmation

        resolved_actor_id = resolve_required_actor_request_field(
            identity,
            actor_id,
            field_name="actor_id",
        )
        try:
            return build_task_readiness_summary(
                task,
                administrator_id=resolved_actor_id,
                materials=materials,
                pending_assignment_materials=pending_assignment_materials,
                latest_recognitions_by_material_id=latest_recognitions_by_material_id,
                invoices=invoices,
                validations_by_invoice_id=validations_by_invoice_id,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
                linked_invoice_ids_by_material_id=linked_invoice_ids_by_material_id,
            )
        except TaskReadinessActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.post("/{task_id}/expense-disputes/{split_id}/resolve")
    def resolve_task_expense_dispute(
        task_id: str,
        split_id: str,
        request: Request,
        payload: ConfirmationDisputeResolve,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        administrator_id = resolve_required_actor_request_field(
            identity,
            payload.administrator_id,
            field_name="administrator_id",
        )
        try:
            ensure_task_administrator(task, actor_id=administrator_id)
        except ExpenseDisputeActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

        split = split_repository.get(split_id)
        if split is None or not split.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="split not found")

        invoice = invoice_repository.get(split.invoice_id)
        if invoice is None or invoice.task_id != task_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="split not found for task",
            )

        confirmation = confirmation_repository.get_by_split(split_id)
        if confirmation is None or confirmation.status is not ConfirmationStatus.DISPUTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="only disputed confirmations can be resolved back to pending",
            )

        updated_confirmation = confirmation_repository.upsert_for_split(
            split_id,
            ConfirmationSubmit(
                actor_id=administrator_id,
                member_id=confirmation.member_id,
                status=ConfirmationStatus.PENDING,
                dispute_reason=confirmation.dispute_reason,
            ),
        )
        record_split_confirmation_audit(
            audit_log_repository,
            actor_id=administrator_id,
            split=split,
            invoice_id=invoice.id,
            task_id=task.id,
            confirmation=updated_confirmation,
            previous_confirmation=confirmation,
            request_id=ensure_request_id(request),
        )
        return updated_confirmation

    @router.put("/{task_id}/members")
    def update_task_members(
        task_id: str,
        payload: TaskMembersUpdate,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        if identity.actor_id != task.administrator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="actor is not allowed to manage task members for this task",
            )
        if task.status != TaskStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="task members can only be updated while task is draft",
            )
        updated = repository.update_member_ids(task_id, payload.member_ids)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"items": enrich_task_member_summaries(updated).member_summaries}

    @router.put("/{task_id}")
    def update_task(
        task_id: str,
        payload: TaskUpdateInput,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        if identity.actor_id != task.administrator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="actor is not allowed to update this task",
            )
        if task.status != TaskStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="task can only be updated while it is draft",
            )
        updated = repository.update_task(task_id, payload)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return enrich_task_member_summaries(updated)

    @router.patch("/{task_id}/status")
    def update_task_status(
        task_id: str,
        payload: TaskStatusUpdate,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        if identity.actor_id != task.administrator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="actor is not allowed to manage task status for this task",
            )

        if not can_transition(task.status, payload.target_status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"cannot transition task from {task.status} to {payload.target_status}",
            )

        if payload.target_status == TaskStatus.OPEN:
            try:
                ensure_task_can_publish(task)
            except TaskPublishValidationError as error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(error),
                ) from error

        if payload.target_status == TaskStatus.READY_TO_EXPORT:
            invoices = invoice_repository.list_by_task(task.id)
            validations_by_invoice_id = {
                invoice.id: validation_repository.list_by_invoice(invoice.id) for invoice in invoices
            }
            splits_by_invoice_id = {
                invoice.id: split_repository.list_by_invoice(invoice.id) for invoice in invoices
            }
            pending_assignment_material_ids = [
                material.id
                for material in material_repository.list_pending_assignment_by_task_hint(task.id)
            ]
            confirmations_by_split_id = {}
            for invoice in invoices:
                for confirmation in confirmation_repository.list_current_by_invoice(invoice.id):
                    confirmations_by_split_id[confirmation.split_id] = confirmation
            try:
                ensure_task_can_enter_ready_to_export(
                    invoices,
                    validations_by_invoice_id=validations_by_invoice_id,
                    splits_by_invoice_id=splits_by_invoice_id,
                    confirmations_by_split_id=confirmations_by_split_id,
                    pending_assignment_material_ids=pending_assignment_material_ids,
                )
            except TaskReviewValidationError as error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(error),
                ) from error

        if payload.target_status == TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(TaskCompletionValidationError()),
            )

        updated_task = repository.update_status(task_id, payload.target_status)
        if updated_task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return enrich_task_member_summaries(updated_task)

    @router.post("/deadline-check")
    def run_task_deadline_check():
        closed_tasks = close_expired_open_tasks(repository)
        return {
            "closed_count": len(closed_tasks),
            "closed_task_ids": [task.id for task in closed_tasks],
        }

    return router
