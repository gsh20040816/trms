from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

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
from trms_backend.domain.materials import MaterialRepository
from trms_backend.domain.recognitions import RecognitionTaskRepository
from trms_backend.domain.splits import ExpenseSplitRepository
from trms_backend.domain.task_review_summary import (
    TaskReviewSummaryActorNotAllowedError,
    build_task_review_summary,
)
from trms_backend.domain.tasks import (
    TaskCreateInput,
    TaskCompletionValidationError,
    MissingTaskInvoiceConfigError,
    TaskMembersUpdate,
    TaskRepository,
    TaskPublishValidationError,
    TaskReviewValidationError,
    TaskStatus,
    TaskStatusUpdate,
    can_transition,
    close_expired_open_tasks,
    ensure_task_can_enter_ready_to_export,
    ensure_task_can_publish,
    resolve_task_create,
)


def build_task_router(
    repository: TaskRepository,
    global_invoice_config_repository: GlobalInvoiceConfigRepository,
    material_reminder_repository: MaterialReminderRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    validation_repository: ValidationRepository,
    recognition_task_repository: RecognitionTaskRepository,
    split_repository: ExpenseSplitRepository,
    confirmation_repository: ConfirmationRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/tasks", tags=["tasks"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    def create_task(payload: TaskCreateInput):
        try:
            task_create = resolve_task_create(payload, global_invoice_config_repository.get())
        except MissingTaskInvoiceConfigError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        return repository.create(task_create)

    @router.get("")
    def list_tasks():
        return repository.list()

    @router.get("/{task_id}")
    def get_task(task_id: str):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return task

    @router.get("/{task_id}/members")
    def get_task_members(task_id: str):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"items": task.member_ids}

    @router.post("/{task_id}/material-reminders", status_code=status.HTTP_201_CREATED)
    def create_material_reminder(task_id: str, payload: MaterialReminderCreate):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        try:
            return create_task_material_reminder(
                task,
                reminder_repository=material_reminder_repository,
                payload=payload,
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
        actor_id: Annotated[str, Query(min_length=1)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        try:
            return {
                "items": list_task_material_reminders(
                    task,
                    reminder_repository=material_reminder_repository,
                    actor_id=actor_id,
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
        actor_id: Annotated[str, Query(min_length=1)],
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
            return build_expense_detail_list(
                task,
                actor_id=actor_id,
                invoices=invoices,
                splits_by_invoice_id=splits_by_invoice_id,
                confirmations_by_split_id=confirmations_by_split_id,
            )
        except ExpenseDetailActorNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.get("/{task_id}/expense-disputes")
    def list_task_expense_disputes(
        task_id: str,
        actor_id: Annotated[str, Query(min_length=1)],
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
                administrator_id=actor_id,
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
        actor_id: Annotated[str, Query(min_length=1)],
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
            return build_overdue_confirmation_list(
                task,
                administrator_id=actor_id,
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
        actor_id: Annotated[str, Query(min_length=1)],
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        materials = material_repository.list_by_task(task_id)
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

        try:
            return build_task_review_summary(
                task,
                administrator_id=actor_id,
                materials=materials,
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

    @router.post("/{task_id}/expense-disputes/{split_id}/resolve")
    def resolve_task_expense_dispute(
        task_id: str,
        split_id: str,
        payload: ConfirmationDisputeResolve,
    ):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

        try:
            ensure_task_administrator(task, actor_id=payload.administrator_id)
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

        return confirmation_repository.upsert_for_split(
            split_id,
            ConfirmationSubmit(
                actor_id=payload.administrator_id,
                member_id=confirmation.member_id,
                status=ConfirmationStatus.PENDING,
                dispute_reason=confirmation.dispute_reason,
            ),
        )

    @router.put("/{task_id}/members")
    def update_task_members(task_id: str, payload: TaskMembersUpdate):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        if task.status != TaskStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="task members can only be updated while task is draft",
            )
        updated = repository.update_member_ids(task_id, payload.member_ids)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"items": updated.member_ids}

    @router.patch("/{task_id}/status")
    def update_task_status(task_id: str, payload: TaskStatusUpdate):
        task = repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

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

        return repository.update_status(task_id, payload.target_status)

    @router.post("/deadline-check")
    def run_task_deadline_check():
        closed_tasks = close_expired_open_tasks(repository)
        return {
            "closed_count": len(closed_tasks),
            "closed_task_ids": [task.id for task in closed_tasks],
        }

    return router
