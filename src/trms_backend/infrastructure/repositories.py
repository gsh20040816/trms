from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from trms_backend.domain.automatic_reminders import (
    AutomaticReminderTaskCreate,
    AutomaticReminderTaskKind,
    AutomaticReminderTaskRecord,
    AutomaticReminderTaskRepository,
    AutomaticReminderTaskStatus,
)
from trms_backend.domain.audit_logs import (
    AuditLogCreate,
    AuditLogRecord,
    AuditLogRepository,
    AuditLogResult,
)
from trms_backend.domain.auth import (
    AuthenticatedUser,
    AuthRepository,
    StoredAuthUser,
    UserCreate,
    UsernameAlreadyExistsError,
    UserRole,
)
from trms_backend.domain.confirmations import (
    ConfirmationRecord,
    ConfirmationRepository,
    ConfirmationStatus,
    ConfirmationSubmit,
)
from trms_backend.domain.exports import (
    ExportArtifactFormat,
    ExportArtifactRecord,
    ExportArtifactKind,
    StoredExportArtifactRecord,
    TaskExportJobCreate,
    TaskExportJobRecord,
    TaskExportJobRepository,
    TaskExportJobStatus,
)
from trms_backend.domain.global_invoice_config import (
    GlobalInvoiceConfig,
    GlobalInvoiceConfigRepository,
)
from trms_backend.domain.system_ai_provider_config import (
    SystemAiProviderConfig,
    SystemAiProviderConfigPatch,
    SystemAiProviderConfigRepository,
    SystemAiProviderOverride,
)
from trms_backend.domain.invoices import (
    ExpenseType,
    InvoiceCreate,
    InvoiceMemberSubmissionStatus,
    InvoiceRecord,
    InvoiceSupportingMaterialLinkRecord,
    ValidationRepository,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from trms_backend.domain.material_reminders import (
    MaterialReminderCreate,
    MaterialReminderRecord,
    MaterialReminderRepository,
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
    TaskUpdateInput,
)
from trms_backend.domain.telegram_bindings import (
    TelegramAccountBindingConflictError,
    TelegramAccountBindingRecord,
    TelegramAccountBindingRepository,
    TelegramAccountBindingUpsert,
)
from trms_backend.infrastructure.database import session_scope
from trms_backend.infrastructure.models import (
    AuthSessionRow,
    AuditLogRow,
    AutomaticReminderTaskRow,
    ConfirmationRow,
    ExpenseSplitRow,
    ExportJobRow,
    GlobalInvoiceConfigRow,
    InvoiceRow,
    InvoiceSupportingMaterialLinkRow,
    MaterialReminderRow,
    MaterialRow,
    RecognitionTaskRow,
    SystemAiProviderConfigRow,
    TaskRow,
    TelegramAccountBindingRow,
    UserAccountRow,
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


class SqlAlchemySystemAiProviderConfigRepository(SystemAiProviderConfigRepository):
    _default_id = "default"

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get(self) -> SystemAiProviderConfig | None:
        with session_scope(self._session_factory) as session:
            row = session.get(SystemAiProviderConfigRow, self._default_id)
            return _system_ai_provider_config_from_row(row) if row else None

    def patch(self, payload: SystemAiProviderConfigPatch) -> SystemAiProviderConfig:
        now = datetime.now(timezone.utc)
        with session_scope(self._session_factory) as session:
            row = session.get(SystemAiProviderConfigRow, self._default_id)
            if row is None:
                row = SystemAiProviderConfigRow(
                    id=self._default_id,
                    created_at=now,
                    updated_at=now,
                    text_llm_base_url=payload.text_llm.base_url,
                    text_llm_model=payload.text_llm.model,
                    text_llm_timeout_seconds=payload.text_llm.timeout_seconds,
                    text_llm_max_retries=payload.text_llm.max_retries,
                    text_llm_api_key=(
                        payload.text_llm.api_key.get_secret_value()
                        if payload.text_llm.api_key is not None
                        else None
                    ),
                    vlm_base_url=payload.vlm.base_url,
                    vlm_model=payload.vlm.model,
                    vlm_timeout_seconds=payload.vlm.timeout_seconds,
                    vlm_max_retries=payload.vlm.max_retries,
                    vlm_api_key=(
                        payload.vlm.api_key.get_secret_value()
                        if payload.vlm.api_key is not None
                        else None
                    ),
                )
            else:
                row.text_llm_base_url = payload.text_llm.base_url
                row.text_llm_model = payload.text_llm.model
                row.text_llm_timeout_seconds = payload.text_llm.timeout_seconds
                row.text_llm_max_retries = payload.text_llm.max_retries
                if "api_key" in payload.text_llm.model_fields_set:
                    row.text_llm_api_key = (
                        payload.text_llm.api_key.get_secret_value()
                        if payload.text_llm.api_key is not None
                        else None
                    )
                row.vlm_base_url = payload.vlm.base_url
                row.vlm_model = payload.vlm.model
                row.vlm_timeout_seconds = payload.vlm.timeout_seconds
                row.vlm_max_retries = payload.vlm.max_retries
                if "api_key" in payload.vlm.model_fields_set:
                    row.vlm_api_key = (
                        payload.vlm.api_key.get_secret_value()
                        if payload.vlm.api_key is not None
                        else None
                    )
                row.updated_at = now
            session.add(row)
        return _system_ai_provider_config_from_row(row)


class SqlAlchemyAuthRepository(AuthRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_user_by_id(self, user_id: str) -> AuthenticatedUser | None:
        with session_scope(self._session_factory) as session:
            row = session.get(UserAccountRow, user_id)
            return _authenticated_user_from_row(row) if row else None

    def create_user(self, data: UserCreate) -> AuthenticatedUser:
        now = datetime.now(timezone.utc)
        row = UserAccountRow(
            id=str(uuid4()),
            username=data.username,
            password_hash=data.password_hash,
            role=data.role.value,
            roles=[role.value for role in data.roles],
            actor_id=data.actor_id,
            display_name=data.display_name,
            member_code=data.member_code,
            registration_source=data.registration_source.value,
            created_by_user_id=data.created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        try:
            with session_scope(self._session_factory) as session:
                session.add(row)
        except IntegrityError as error:
            raise UsernameAlreadyExistsError(data.username) from error
        return _authenticated_user_from_row(row)

    def get_user_by_username(self, username: str) -> StoredAuthUser | None:
        with session_scope(self._session_factory) as session:
            row = session.scalars(
                select(UserAccountRow).where(UserAccountRow.username == username)
            ).first()
            return _stored_auth_user_from_row(row) if row else None

    def get_user_by_token_hash(self, token_hash: str) -> AuthenticatedUser | None:
        with session_scope(self._session_factory) as session:
            record = session.execute(
                select(UserAccountRow, AuthSessionRow.active_role)
                .join(AuthSessionRow, AuthSessionRow.user_id == UserAccountRow.id)
                .where(
                    AuthSessionRow.token_hash == token_hash,
                    AuthSessionRow.revoked_at.is_(None),
                )
            ).first()
            if record is None:
                return None
            row, active_role = record
            return _authenticated_user_from_row(row, active_role=UserRole(active_role))

    def list_users_by_member_identifiers(self, identifiers: list[str]) -> list[AuthenticatedUser]:
        normalized_identifiers = [identifier.strip() for identifier in identifiers if identifier.strip()]
        if not normalized_identifiers:
            return []

        with session_scope(self._session_factory) as session:
            rows = session.scalars(select(UserAccountRow)).all()

        matched_users = [
            _authenticated_user_from_row(row)
            for row in rows
            if row.member_code in normalized_identifiers or row.actor_id in normalized_identifiers
        ]
        matched_users.sort(key=lambda user: normalized_identifiers.index(user.member_code or user.actor_id))
        return matched_users

    def search_users(
        self,
        *,
        keyword: str,
        roles: tuple[UserRole, ...],
        limit: int,
    ) -> list[AuthenticatedUser]:
        normalized_keyword = keyword.strip().lower()
        if not normalized_keyword or limit <= 0:
            return []

        with session_scope(self._session_factory) as session:
            rows = session.scalars(select(UserAccountRow).order_by(UserAccountRow.created_at)).all()

        matched_users: list[AuthenticatedUser] = []
        for row in rows:
            row_roles = _roles_from_row(row)
            if roles and not any(role in row_roles for role in roles):
                continue

            searchable_values = (
                row.username,
                row.display_name,
                row.member_code or "",
                row.actor_id,
            )
            if not any(normalized_keyword in value.lower() for value in searchable_values if value):
                continue

            matched_users.append(_authenticated_user_from_row(row))
            if len(matched_users) >= limit:
                break

        return matched_users

    def create_session(self, *, user_id: str, token_hash: str, active_role: UserRole) -> None:
        with session_scope(self._session_factory) as session:
            session.add(
                AuthSessionRow(
                    id=str(uuid4()),
                    user_id=user_id,
                    token_hash=token_hash,
                    active_role=active_role.value,
                    created_at=datetime.now(timezone.utc),
                    revoked_at=None,
                )
            )

    def revoke_session(self, *, token_hash: str) -> bool:
        with session_scope(self._session_factory) as session:
            row = session.scalars(
                select(AuthSessionRow).where(
                    AuthSessionRow.token_hash == token_hash,
                    AuthSessionRow.revoked_at.is_(None),
                )
            ).first()
            if row is None:
                return False
            row.revoked_at = datetime.now(timezone.utc)
            session.add(row)
            return True

    def switch_session_active_role(
        self,
        *,
        token_hash: str,
        active_role: UserRole,
    ) -> AuthenticatedUser | None:
        with session_scope(self._session_factory) as session:
            session_row = session.scalars(
                select(AuthSessionRow).where(
                    AuthSessionRow.token_hash == token_hash,
                    AuthSessionRow.revoked_at.is_(None),
                )
            ).first()
            if session_row is None:
                return None
            user_row = session.get(UserAccountRow, session_row.user_id)
            if user_row is None:
                return None
            session_row.active_role = active_role.value
            session.add(session_row)
            return _authenticated_user_from_row(user_row, active_role=active_role)

    def grant_role_to_user(
        self,
        *,
        user_id: str,
        role: UserRole,
    ) -> tuple[AuthenticatedUser, bool] | None:
        with session_scope(self._session_factory) as session:
            row = session.get(UserAccountRow, user_id)
            if row is None:
                return None

            roles = _roles_from_row(row)
            already_assigned = role in roles
            if not already_assigned:
                roles.append(role)
                row.roles = [assigned_role.value for assigned_role in roles]
                row.updated_at = datetime.now(timezone.utc)
                session.add(row)
            return _authenticated_user_from_row(row), already_assigned

    def update_user_profile(
        self,
        *,
        user_id: str,
        display_name: str,
        member_code: str | None,
    ) -> AuthenticatedUser | None:
        with session_scope(self._session_factory) as session:
            row = session.get(UserAccountRow, user_id)
            if row is None:
                return None
            row.display_name = display_name
            row.member_code = member_code
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
            return _authenticated_user_from_row(row)

    def update_user_password(
        self,
        *,
        user_id: str,
        password_hash: str,
    ) -> AuthenticatedUser | None:
        with session_scope(self._session_factory) as session:
            row = session.get(UserAccountRow, user_id)
            if row is None:
                return None
            row.password_hash = password_hash
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
            return _authenticated_user_from_row(row)

    def count_users_with_roles(self, roles: tuple[UserRole, ...]) -> int:
        if not roles:
            return 0
        with session_scope(self._session_factory) as session:
            rows = session.scalars(select(UserAccountRow)).all()
            return sum(
                1
                for row in rows
                if any(role in _roles_from_row(row) for role in roles)
            )


class SqlAlchemyAuditLogRepository(AuditLogRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, data: AuditLogCreate) -> AuditLogRecord:
        row = AuditLogRow(
            id=str(uuid4()),
            actor_id=data.actor_id,
            object_type=data.object_type,
            object_id=data.object_id,
            action=data.action,
            result=data.result.value,
            summary=data.summary,
            detail=data.detail,
            task_id=data.task_id,
            request_id=data.request_id,
            created_at=datetime.now(timezone.utc),
        )
        with session_scope(self._session_factory) as session:
            session.add(row)
        return _audit_log_from_row(row)

    def list_by_object(self, *, object_type: str, object_id: str) -> list[AuditLogRecord]:
        normalized_object_type = object_type.strip()
        normalized_object_id = object_id.strip()
        if not normalized_object_type or not normalized_object_id:
            return []

        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(AuditLogRow)
                .where(
                    AuditLogRow.object_type == normalized_object_type,
                    AuditLogRow.object_id == normalized_object_id,
                )
                .order_by(AuditLogRow.created_at)
            ).all()
            return [_audit_log_from_row(row) for row in rows]


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

    def list_for_member(self, member_id: str) -> list[ReimbursementTask]:
        normalized_member_id = member_id.strip()
        if not normalized_member_id:
            return []

        with session_scope(self._session_factory) as session:
            rows = session.scalars(select(TaskRow).order_by(TaskRow.created_at)).all()
            return [
                _task_from_row(row)
                for row in rows
                if normalized_member_id in row.member_ids
            ]

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

    def update_task(
        self,
        task_id: str,
        payload: TaskUpdateInput,
    ) -> ReimbursementTask | None:
        with session_scope(self._session_factory) as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return None
            row.competition_name = payload.competition_name
            row.competition_location = payload.competition_location
            row.competition_start_date = payload.competition_start_date
            row.competition_end_date = payload.competition_end_date
            row.deadline = payload.deadline
            row.member_ids = payload.member_ids
            row.fee_categories = payload.fee_categories
            if payload.administrator_ids is not None:
                row.administrator_ids = payload.administrator_ids
            if payload.administrator_id is not None:
                row.administrator_id = payload.administrator_id
            if payload.project_info is not None:
                row.project_info = payload.project_info
            if payload.reimburser_info is not None:
                row.reimburser_info = payload.reimburser_info
            row.invoice_title = payload.invoice_title
            row.tax_number = payload.tax_number
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

    def list_pending_assignment_by_task_hint(self, task_id: str) -> list[MaterialRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(MaterialRow)
                .where(
                    MaterialRow.status == MaterialStatus.PENDING_ASSIGNMENT.value,
                    MaterialRow.task_id_hint == task_id,
                )
                .order_by(MaterialRow.created_at)
            ).all()
            return [_material_from_row(row) for row in rows]

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

    def mark_deleted(self, material_id: str) -> MaterialRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(MaterialRow, material_id)
            if row is None or row.status != MaterialStatus.ASSIGNED.value:
                return None
            row.status = MaterialStatus.DELETED.value
            session.add(row)
        return _material_from_row(row)

    def update_material_type(
        self,
        *,
        material_id: str,
        material_type: MaterialType,
    ) -> MaterialRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(MaterialRow, material_id)
            if row is None or row.status != MaterialStatus.ASSIGNED.value:
                return None
            row.material_type = material_type.value
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


class SqlAlchemyTelegramAccountBindingRepository(TelegramAccountBindingRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def upsert(self, data: TelegramAccountBindingUpsert) -> TelegramAccountBindingRecord:
        now = datetime.now(timezone.utc)
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(TelegramAccountBindingRow)
                .where(TelegramAccountBindingRow.telegram_user_id == data.telegram_user_id)
                .limit(1)
            )
            if row is not None:
                if row.member_id != data.member_id:
                    raise TelegramAccountBindingConflictError(
                        "telegram user is already bound to another member: "
                        f"{data.telegram_user_id}"
                    )
                row.telegram_username = data.telegram_username
                row.updated_at = now
                session.add(row)
                return _telegram_account_binding_from_row(row)

            member_row = session.scalar(
                select(TelegramAccountBindingRow)
                .where(TelegramAccountBindingRow.member_id == data.member_id)
                .limit(1)
            )
            if member_row is not None:
                raise TelegramAccountBindingConflictError(
                    "member is already bound to another telegram user: "
                    f"{data.member_id}"
                )

            row = TelegramAccountBindingRow(
                id=str(uuid4()),
                created_at=now,
                updated_at=now,
                **data.model_dump(),
            )
            session.add(row)
        return _telegram_account_binding_from_row(row)

    def get_by_telegram_user_id(self, telegram_user_id: int) -> TelegramAccountBindingRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(TelegramAccountBindingRow)
                .where(TelegramAccountBindingRow.telegram_user_id == telegram_user_id)
                .limit(1)
            )
            return _telegram_account_binding_from_row(row) if row else None

    def get_by_member_id(self, member_id: str) -> TelegramAccountBindingRecord | None:
        normalized_member_id = member_id.strip()
        if not normalized_member_id:
            return None

        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(TelegramAccountBindingRow)
                .where(TelegramAccountBindingRow.member_id == normalized_member_id)
                .limit(1)
            )
            return _telegram_account_binding_from_row(row) if row else None


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
                    member_submission_status=InvoiceMemberSubmissionStatus.UNSUBMITTED.value,
                    submitted_by_member_id=None,
                    submitted_at=None,
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
                row.corporate_transfer_reference = data.corporate_transfer_reference
                row.is_paper_invoice = data.is_paper_invoice
                row.paper_invoice_received = data.paper_invoice_received
                row.paper_invoice_received_at = data.paper_invoice_received_at
                row.paper_invoice_received_by = data.paper_invoice_received_by
                row.amount_cents = data.amount_cents
                row.expense_type = data.expense_type.value
                row.updated_at = now
            session.add(row)
        return _invoice_from_row(row)

    def get(self, invoice_id: str) -> InvoiceRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(InvoiceRow, invoice_id)
            return _invoice_from_row(row) if row else None

    def get_by_material(self, material_id: str) -> InvoiceRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(InvoiceRow)
                .where(InvoiceRow.material_id == material_id)
                .order_by(InvoiceRow.created_at)
                .limit(1)
            )
            return _invoice_from_row(row) if row else None

    def delete_unsubmitted_invoice(self, invoice_id: str) -> InvoiceRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(InvoiceRow, invoice_id)
            if row is None:
                return None
            deleted_invoice = _invoice_from_row(row)
            session.execute(
                delete(ValidationResultRow).where(
                    ValidationResultRow.target_type == "invoice",
                    ValidationResultRow.target_id == invoice_id,
                )
            )
            session.execute(
                delete(ConfirmationRow).where(
                    ConfirmationRow.split_id.in_(
                        select(ExpenseSplitRow.id).where(ExpenseSplitRow.invoice_id == invoice_id)
                    )
                )
            )
            session.execute(delete(ExpenseSplitRow).where(ExpenseSplitRow.invoice_id == invoice_id))
            session.execute(
                delete(InvoiceSupportingMaterialLinkRow).where(
                    InvoiceSupportingMaterialLinkRow.invoice_id == invoice_id
                )
            )
            session.delete(row)
        return deleted_invoice

    def list_by_task(self, task_id: str) -> list[InvoiceRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(InvoiceRow).where(InvoiceRow.task_id == task_id).order_by(InvoiceRow.created_at)
            ).all()
            return [_invoice_from_row(row) for row in rows]

    def list_by_supporting_material(self, material_id: str) -> list[InvoiceRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(InvoiceRow)
                .join(
                    InvoiceSupportingMaterialLinkRow,
                    InvoiceSupportingMaterialLinkRow.invoice_id == InvoiceRow.id,
                )
                .where(InvoiceSupportingMaterialLinkRow.material_id == material_id)
                .order_by(InvoiceSupportingMaterialLinkRow.created_at, InvoiceRow.created_at)
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

    def update_member_submission_status(
        self,
        *,
        invoice_id: str,
        status: InvoiceMemberSubmissionStatus,
        submitted_by_member_id: str | None,
        submitted_at: datetime | None,
    ) -> InvoiceRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(InvoiceRow, invoice_id)
            if row is None:
                return None
            row.member_submission_status = status.value
            row.submitted_by_member_id = submitted_by_member_id
            row.submitted_at = submitted_at
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
        return _invoice_from_row(row)

    def confirm_paper_invoice_received(
        self,
        *,
        invoice_id: str,
        received_by: str,
        received_at: datetime,
    ) -> InvoiceRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(InvoiceRow, invoice_id)
            if row is None:
                return None
            row.paper_invoice_received = True
            row.paper_invoice_received_by = received_by
            row.paper_invoice_received_at = received_at
            row.updated_at = received_at
            session.add(row)
        return _invoice_from_row(row)


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

    def list_pending(self, *, limit: int) -> list[RecognitionTaskRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(RecognitionTaskRow)
                .where(RecognitionTaskRow.status == RecognitionTaskStatus.PENDING.value)
                .order_by(RecognitionTaskRow.created_at)
                .limit(limit)
            ).all()
            return [_recognition_task_from_row(row) for row in rows]

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
        expected_current_status: RecognitionTaskStatus | None = None,
    ) -> RecognitionTaskRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(RecognitionTaskRow, recognition_task_id)
            if row is None:
                return None
            if (
                expected_current_status is not None
                and row.status != expected_current_status.value
            ):
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
        with session_scope(self._session_factory) as session:
            active_rows = session.scalars(
                select(ExpenseSplitRow)
                .where(
                    ExpenseSplitRow.invoice_id == invoice_id,
                    ExpenseSplitRow.is_active.is_(True),
                )
                .order_by(ExpenseSplitRow.created_at)
            ).all()
            existing_rows_by_member_id = {row.member_id: row for row in active_rows}

            rows: list[ExpenseSplitRow] = []
            for item in items:
                existing_row = existing_rows_by_member_id.pop(item.member_id, None)
                if existing_row is None:
                    row = ExpenseSplitRow(
                        id=str(uuid4()),
                        invoice_id=invoice_id,
                        member_id=item.member_id,
                        amount_cents=item.amount_cents,
                        note=item.note,
                        version=1,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(row)
                    rows.append(row)
                    continue

                split_changed = (
                    existing_row.amount_cents != item.amount_cents or existing_row.note != item.note
                )
                if split_changed:
                    previous_version = existing_row.version
                    had_current_confirmation = session.scalar(
                        select(ConfirmationRow.id).where(
                            ConfirmationRow.split_id == existing_row.id,
                            ConfirmationRow.member_id == existing_row.member_id,
                            ConfirmationRow.split_version == previous_version,
                        )
                    )
                    existing_row.version = previous_version + 1
                    existing_row.amount_cents = item.amount_cents
                    existing_row.note = item.note
                    existing_row.updated_at = now
                    if had_current_confirmation is not None:
                        session.add(
                            ConfirmationRow(
                                id=str(uuid4()),
                                split_id=existing_row.id,
                                member_id=existing_row.member_id,
                                split_version=existing_row.version,
                                split_amount_cents=item.amount_cents,
                                split_note=item.note,
                                status=ConfirmationStatus.PENDING.value,
                                dispute_reason=None,
                                confirmed_at=now,
                                updated_at=now,
                            )
                        )
                else:
                    existing_row.amount_cents = item.amount_cents
                    existing_row.note = item.note
                session.add(existing_row)
                rows.append(existing_row)

            for removed_row in existing_rows_by_member_id.values():
                removed_row.is_active = False
                removed_row.updated_at = now
                session.add(removed_row)
        return [_split_from_row(row) for row in rows]

    def list_by_invoice(self, invoice_id: str) -> list[ExpenseSplitRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(ExpenseSplitRow)
                .where(
                    ExpenseSplitRow.invoice_id == invoice_id,
                    ExpenseSplitRow.is_active.is_(True),
                )
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

    def get_by_split(self, split_id: str) -> ConfirmationRecord | None:
        with session_scope(self._session_factory) as session:
            split_row = session.get(ExpenseSplitRow, split_id)
            if split_row is None or not split_row.is_active:
                return None
            row = session.scalar(
                select(ConfirmationRow).where(
                    ConfirmationRow.split_id == split_id,
                    ConfirmationRow.member_id == split_row.member_id,
                    ConfirmationRow.split_version == split_row.version,
                )
            )
            return (
                _confirmation_from_row(
                    row,
                    is_current=True,
                )
                if row
                else None
            )

    def upsert_for_split(
        self,
        split_id: str,
        payload: ConfirmationSubmit,
    ) -> ConfirmationRecord:
        now = datetime.now(timezone.utc)
        with session_scope(self._session_factory) as session:
            split_row = session.get(ExpenseSplitRow, split_id)
            if split_row is None or not split_row.is_active:
                raise ValueError("split not found")
            row = session.scalar(
                select(ConfirmationRow).where(
                    ConfirmationRow.split_id == split_id,
                    ConfirmationRow.member_id == payload.member_id,
                    ConfirmationRow.split_version == split_row.version,
                )
            )
            if row is None:
                row = ConfirmationRow(
                    id=str(uuid4()),
                    split_id=split_id,
                    member_id=payload.member_id,
                    split_version=split_row.version,
                    split_amount_cents=split_row.amount_cents,
                    split_note=split_row.note,
                    confirmed_at=now,
                    updated_at=now,
                    status=payload.status.value,
                    dispute_reason=payload.dispute_reason,
                )
            else:
                row.split_amount_cents = split_row.amount_cents
                row.split_note = split_row.note
                row.status = payload.status.value
                row.dispute_reason = payload.dispute_reason
                row.updated_at = now
            session.add(row)
        return _confirmation_from_row(row, is_current=True)

    def list_current_by_invoice(self, invoice_id: str) -> list[ConfirmationRecord]:
        with session_scope(self._session_factory) as session:
            split_rows = session.scalars(
                select(ExpenseSplitRow)
                .where(
                    ExpenseSplitRow.invoice_id == invoice_id,
                    ExpenseSplitRow.is_active.is_(True),
                )
                .order_by(ExpenseSplitRow.created_at)
            ).all()
            split_rows_by_id = {row.id: row for row in split_rows}
            rows = session.scalars(
                select(ConfirmationRow)
                .join(ExpenseSplitRow, ConfirmationRow.split_id == ExpenseSplitRow.id)
                .where(
                    ExpenseSplitRow.invoice_id == invoice_id,
                    ExpenseSplitRow.is_active.is_(True),
                )
                .order_by(ConfirmationRow.confirmed_at)
            ).all()
            return [
                _confirmation_from_row(row, is_current=True)
                for row in rows
                if row.split_version == split_rows_by_id[row.split_id].version
            ]

    def list_by_invoice(self, invoice_id: str) -> list[ConfirmationRecord]:
        with session_scope(self._session_factory) as session:
            split_rows = session.scalars(
                select(ExpenseSplitRow)
                .where(ExpenseSplitRow.invoice_id == invoice_id)
                .order_by(ExpenseSplitRow.created_at)
            ).all()
            split_rows_by_id = {row.id: row for row in split_rows}
            rows = session.scalars(
                select(ConfirmationRow)
                .join(ExpenseSplitRow, ConfirmationRow.split_id == ExpenseSplitRow.id)
                .where(ExpenseSplitRow.invoice_id == invoice_id)
                .order_by(ConfirmationRow.confirmed_at)
            ).all()
            return [
                _confirmation_from_row(
                    row,
                    is_current=(
                        split_rows_by_id[row.split_id].is_active
                        and row.split_version == split_rows_by_id[row.split_id].version
                    ),
                )
                for row in rows
            ]


class SqlAlchemyMaterialReminderRepository(MaterialReminderRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, *, task_id: str, data: MaterialReminderCreate) -> MaterialReminderRecord:
        row = MaterialReminderRow(
            id=str(uuid4()),
            task_id=task_id,
            administrator_id=data.administrator_id,
            member_id=data.member_id,
            content=data.content,
            created_at=datetime.now(timezone.utc),
        )
        with session_scope(self._session_factory) as session:
            session.add(row)
        return _material_reminder_from_row(row)

    def list_by_task(self, task_id: str) -> list[MaterialReminderRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(MaterialReminderRow)
                .where(MaterialReminderRow.task_id == task_id)
                .order_by(MaterialReminderRow.created_at)
            ).all()
            return [_material_reminder_from_row(row) for row in rows]


class SqlAlchemyAutomaticReminderTaskRepository(AutomaticReminderTaskRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(
        self,
        *,
        task_id: str,
        data: AutomaticReminderTaskCreate,
    ) -> AutomaticReminderTaskRecord:
        now = datetime.now(timezone.utc)
        row = AutomaticReminderTaskRow(
            id=str(uuid4()),
            task_id=task_id,
            member_id=data.member_id,
            requested_by=data.requested_by,
            kind=data.kind.value,
            status=AutomaticReminderTaskStatus.PENDING.value,
            summary=data.summary,
            payload=data.payload,
            deduplication_key=data.deduplication_key,
            created_at=now,
            updated_at=now,
        )
        with session_scope(self._session_factory) as session:
            session.add(row)
        return _automatic_reminder_task_from_row(row)

    def get_by_deduplication_key(
        self,
        *,
        task_id: str,
        deduplication_key: str,
    ) -> AutomaticReminderTaskRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(AutomaticReminderTaskRow).where(
                    AutomaticReminderTaskRow.task_id == task_id,
                    AutomaticReminderTaskRow.deduplication_key == deduplication_key,
                )
            )
            return _automatic_reminder_task_from_row(row) if row else None

    def list_by_task(self, task_id: str) -> list[AutomaticReminderTaskRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(AutomaticReminderTaskRow)
                .where(AutomaticReminderTaskRow.task_id == task_id)
                .order_by(AutomaticReminderTaskRow.created_at)
            ).all()
            return [_automatic_reminder_task_from_row(row) for row in rows]


class SqlAlchemyExportJobRepository(TaskExportJobRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(
        self,
        *,
        task_id: str,
        data: TaskExportJobCreate,
    ) -> TaskExportJobRecord:
        now = datetime.now(timezone.utc)
        stored_parameters = dict(data.parameters)
        if data.task_status_at_request is not None:
            stored_parameters["_task_status_at_request"] = data.task_status_at_request.value
        if data.task_data_version is not None:
            stored_parameters["_task_data_version"] = data.task_data_version
        row = ExportJobRow(
            id=str(uuid4()),
            task_id=task_id,
            requested_by=data.requested_by,
            kind=data.kind.value,
            format=data.format.value,
            status=TaskExportJobStatus.PENDING.value,
            parameters=stored_parameters,
            failure_reason=None,
            created_at=now,
            updated_at=now,
            started_at=None,
            finished_at=None,
        )
        with session_scope(self._session_factory) as session:
            session.add(row)
        return _export_job_from_row(row)

    def get(self, export_job_id: str) -> TaskExportJobRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(ExportJobRow, export_job_id)
            return _export_job_from_row(row) if row else None

    def list_by_task(self, task_id: str) -> list[TaskExportJobRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(ExportJobRow)
                .where(ExportJobRow.task_id == task_id)
                .order_by(ExportJobRow.created_at)
            ).all()
            return [_export_job_from_row(row) for row in rows]

    def list_pending(self, *, limit: int = 10) -> list[TaskExportJobRecord]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(ExportJobRow)
                .where(ExportJobRow.status == TaskExportJobStatus.PENDING.value)
                .order_by(ExportJobRow.created_at)
                .limit(limit)
            ).all()
            return [_export_job_from_row(row) for row in rows]

    def update_status(
        self,
        export_job_id: str,
        *,
        target_status: TaskExportJobStatus,
        failure_reason: str | None = None,
        artifact: StoredExportArtifactRecord | None = None,
        expected_current_status: TaskExportJobStatus | None = None,
    ) -> TaskExportJobRecord | None:
        with session_scope(self._session_factory) as session:
            row = session.get(ExportJobRow, export_job_id)
            if row is None:
                return None
            if (
                expected_current_status is not None
                and row.status != expected_current_status.value
            ):
                return None

            now = datetime.now(timezone.utc)
            row.status = target_status.value
            row.updated_at = now
            if target_status is TaskExportJobStatus.RUNNING and row.started_at is None:
                row.started_at = now
            if target_status in {TaskExportJobStatus.SUCCEEDED, TaskExportJobStatus.FAILED}:
                row.finished_at = now
            parameters = dict(row.parameters or {})
            if artifact is not None:
                parameters["_artifact"] = artifact.model_dump(mode="json")
            elif target_status is not TaskExportJobStatus.SUCCEEDED:
                parameters.pop("_artifact", None)
            row.parameters = parameters
            row.failure_reason = failure_reason if target_status is TaskExportJobStatus.FAILED else None
            session.add(row)
        return _export_job_from_row(row)


def _task_from_row(row: TaskRow) -> ReimbursementTask:
    administrator_ids = list(row.administrator_ids) if row.administrator_ids else [row.administrator_id]
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
        administrator_ids=administrator_ids,
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


def _system_ai_provider_config_from_row(
    row: SystemAiProviderConfigRow,
) -> SystemAiProviderConfig:
    return SystemAiProviderConfig(
        text_llm=SystemAiProviderOverride(
            base_url=row.text_llm_base_url,
            model=row.text_llm_model,
            timeout_seconds=row.text_llm_timeout_seconds,
            max_retries=row.text_llm_max_retries,
            api_key=row.text_llm_api_key,
        ),
        vlm=SystemAiProviderOverride(
            base_url=row.vlm_base_url,
            model=row.vlm_model,
            timeout_seconds=row.vlm_timeout_seconds,
            max_retries=row.vlm_max_retries,
            api_key=row.vlm_api_key,
        ),
    )


def _roles_from_row(row: UserAccountRow) -> list[UserRole]:
    normalized_roles: list[UserRole] = []
    for raw_role in row.roles or [row.role]:
        role = UserRole(raw_role)
        if role not in normalized_roles:
            normalized_roles.append(role)
    if not normalized_roles:
        normalized_roles.append(UserRole(row.role))
    return normalized_roles


def _resolve_active_role(row: UserAccountRow, active_role: UserRole | None) -> UserRole:
    available_roles = _roles_from_row(row)
    if active_role is not None and active_role in available_roles:
        return active_role
    fallback_role = UserRole(row.role)
    if fallback_role in available_roles:
        return fallback_role
    return available_roles[0]


def _authenticated_user_from_row(
    row: UserAccountRow,
    *,
    active_role: UserRole | None = None,
) -> AuthenticatedUser:
    roles = _roles_from_row(row)
    return AuthenticatedUser(
        id=row.id,
        username=row.username,
        role=_resolve_active_role(row, active_role),
        roles=roles,
        actor_id=row.actor_id,
        display_name=row.display_name,
        member_code=row.member_code,
        created_at=_ensure_utc_datetime(row.created_at),
        updated_at=_ensure_utc_datetime(row.updated_at),
    )


def _stored_auth_user_from_row(row: UserAccountRow) -> StoredAuthUser:
    roles = _roles_from_row(row)
    return StoredAuthUser(
        id=row.id,
        username=row.username,
        password_hash=row.password_hash,
        role=UserRole(row.role),
        roles=roles,
        actor_id=row.actor_id,
        display_name=row.display_name,
        member_code=row.member_code,
        created_at=_ensure_utc_datetime(row.created_at),
        updated_at=_ensure_utc_datetime(row.updated_at),
    )


def _audit_log_from_row(row: AuditLogRow) -> AuditLogRecord:
    return AuditLogRecord(
        id=row.id,
        actor_id=row.actor_id,
        object_type=row.object_type,
        object_id=row.object_id,
        action=row.action,
        result=AuditLogResult(row.result),
        summary=row.summary,
        detail=dict(row.detail or {}),
        task_id=row.task_id,
        request_id=row.request_id,
        created_at=_ensure_utc_datetime(row.created_at),
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


def _telegram_account_binding_from_row(
    row: TelegramAccountBindingRow,
) -> TelegramAccountBindingRecord:
    return TelegramAccountBindingRecord(
        id=row.id,
        telegram_user_id=row.telegram_user_id,
        member_id=row.member_id,
        telegram_username=row.telegram_username,
        created_at=row.created_at,
        updated_at=row.updated_at,
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
        corporate_transfer_reference=row.corporate_transfer_reference,
        is_paper_invoice=row.is_paper_invoice,
        paper_invoice_received=row.paper_invoice_received,
        paper_invoice_received_at=row.paper_invoice_received_at,
        paper_invoice_received_by=row.paper_invoice_received_by,
        amount_cents=row.amount_cents,
        expense_type=ExpenseType(row.expense_type),
        member_submission_status=InvoiceMemberSubmissionStatus(row.member_submission_status),
        submitted_by_member_id=row.submitted_by_member_id,
        submitted_at=row.submitted_at,
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
        version=row.version,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _confirmation_from_row(row: ConfirmationRow, *, is_current: bool) -> ConfirmationRecord:
    return ConfirmationRecord(
        id=row.id,
        split_id=row.split_id,
        member_id=row.member_id,
        split_version=row.split_version,
        split_amount_cents=row.split_amount_cents,
        split_note=row.split_note,
        is_current=is_current,
        status=ConfirmationStatus(row.status),
        dispute_reason=row.dispute_reason,
        confirmed_at=row.confirmed_at,
        updated_at=row.updated_at,
    )


def _material_reminder_from_row(row: MaterialReminderRow) -> MaterialReminderRecord:
    return MaterialReminderRecord(
        id=row.id,
        task_id=row.task_id,
        administrator_id=row.administrator_id,
        member_id=row.member_id,
        content=row.content,
        created_at=_ensure_utc_datetime(row.created_at),
    )


def _automatic_reminder_task_from_row(
    row: AutomaticReminderTaskRow,
) -> AutomaticReminderTaskRecord:
    return AutomaticReminderTaskRecord(
        id=row.id,
        task_id=row.task_id,
        member_id=row.member_id,
        requested_by=row.requested_by,
        kind=AutomaticReminderTaskKind(row.kind),
        status=AutomaticReminderTaskStatus(row.status),
        summary=row.summary,
        payload=dict(row.payload),
        deduplication_key=row.deduplication_key,
        created_at=_ensure_utc_datetime(row.created_at),
        updated_at=_ensure_utc_datetime(row.updated_at),
    )


def _export_job_from_row(row: ExportJobRow) -> TaskExportJobRecord:
    parameters = dict(row.parameters or {})
    raw_task_status = parameters.pop("_task_status_at_request", None)
    task_data_version = parameters.pop("_task_data_version", None)
    raw_artifact = parameters.pop("_artifact", None)
    artifact = None
    artifact_storage_key = None
    if isinstance(raw_artifact, dict):
        storage_key = raw_artifact.get("storage_key")
        filename = raw_artifact.get("filename")
        sha256 = raw_artifact.get("sha256")
        if (
            isinstance(storage_key, str)
            and isinstance(filename, str)
            and isinstance(sha256, str)
        ):
            artifact_storage_key = storage_key
            artifact = ExportArtifactRecord(
                filename=filename,
                content_type=(
                    raw_artifact.get("content_type")
                    if isinstance(raw_artifact.get("content_type"), str)
                    else None
                ),
                size_bytes=(
                    raw_artifact.get("size_bytes")
                    if isinstance(raw_artifact.get("size_bytes"), int)
                    else 0
                ),
                sha256=sha256,
            )
    return TaskExportJobRecord(
        id=row.id,
        task_id=row.task_id,
        requested_by=row.requested_by,
        kind=ExportArtifactKind(row.kind),
        format=ExportArtifactFormat(row.format),
        status=TaskExportJobStatus(row.status),
        parameters=parameters,
        task_status_at_request=(
            TaskStatus(raw_task_status) if isinstance(raw_task_status, str) else None
        ),
        task_data_version=task_data_version if isinstance(task_data_version, str) else None,
        artifact=artifact,
        artifact_storage_key=artifact_storage_key,
        failure_reason=row.failure_reason,
        created_at=_ensure_utc_datetime(row.created_at),
        updated_at=_ensure_utc_datetime(row.updated_at),
        started_at=(
            _ensure_utc_datetime(row.started_at) if row.started_at is not None else None
        ),
        finished_at=(
            _ensure_utc_datetime(row.finished_at) if row.finished_at is not None else None
        ),
    )


def _ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)
