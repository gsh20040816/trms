from trms_backend.domain.audit_logs import (
    AuditLogCreate,
    AuditLogResult,
    REDACTED_AUDIT_VALUE,
    TRUNCATED_AUDIT_VALUE_SUFFIX,
)
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import SqlAlchemyAuditLogRepository


def test_audit_log_create_sanitizes_sensitive_detail_and_summary():
    entry = AuditLogCreate(
        actor_id="admin-1",
        object_type="material",
        object_id="material-1",
        action="submit",
        result=AuditLogResult.FAILED,
        summary="upload failed token=secret-token",
        detail={
            "api_token": "secret-token",
            "password": "p@ssw0rd",
            "document_text": "A" * 1024,
            "failure_reason": "  content type mismatch  ",
            "nested": {
                "authorization": "Bearer secret",
                "note": "B" * 400,
            },
        },
    )

    assert entry.summary == "upload failed token=[REDACTED]"
    assert entry.detail["api_token"] == REDACTED_AUDIT_VALUE
    assert entry.detail["password"] == REDACTED_AUDIT_VALUE
    assert entry.detail["document_text"] == REDACTED_AUDIT_VALUE
    assert entry.detail["failure_reason"] == "content type mismatch"
    assert entry.detail["nested"]["authorization"] == REDACTED_AUDIT_VALUE
    assert entry.detail["nested"]["note"].endswith(TRUNCATED_AUDIT_VALUE_SUFFIX)


def test_sqlalchemy_audit_log_repository_persists_sanitized_records(tmp_path):
    session_factory = build_session_factory(f"sqlite:///{tmp_path}/test.db")
    init_database(session_factory)
    repository = SqlAlchemyAuditLogRepository(session_factory)

    created = repository.create(
        AuditLogCreate(
            actor_id="admin-1",
            object_type="material",
            object_id="material-1",
            action="claim_pending_assignment",
            result=AuditLogResult.SUCCEEDED,
            summary="claim pending assignment for material-1",
            detail={
                "request_id": "req_123",
                "file_content": "raw bytes here",
                "outcome": "claimed",
            },
            request_id="req_123",
        )
    )

    assert created.result is AuditLogResult.SUCCEEDED
    assert created.detail["file_content"] == REDACTED_AUDIT_VALUE
    assert created.detail["outcome"] == "claimed"
    assert created.task_id is None
    assert created.request_id == "req_123"

    listed = repository.list_by_object(object_type="material", object_id="material-1")

    assert len(listed) == 1
    assert listed[0].id == created.id
    assert listed[0].detail["file_content"] == REDACTED_AUDIT_VALUE
