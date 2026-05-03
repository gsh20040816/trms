from alembic import command
from sqlalchemy import inspect

import pytest
import trms_backend.infrastructure.database as database_module

from trms_backend.infrastructure.database import (
    DatabaseSchemaNotReadyError,
    build_alembic_config,
    build_session_factory,
    get_alembic_head_revisions,
    init_database,
)


def test_build_engine_sets_sqlite_busy_timeout(monkeypatch):
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        database_module,
        "create_engine",
        lambda database_url, connect_args: calls.append(
            {
                "database_url": database_url,
                "connect_args": connect_args,
            }
        )
        or object(),
    )

    database_module.build_engine("sqlite:///./test.db")

    assert calls == [
        {
            "database_url": "sqlite:///./test.db",
            "connect_args": {
                "check_same_thread": False,
                "timeout": database_module.SQLITE_BUSY_TIMEOUT_SECONDS,
            },
        }
    ]


def test_init_database_bootstraps_schema_for_local_sqlite(tmp_path):
    session_factory = build_session_factory(f"sqlite:///{tmp_path}/development.db")

    init_database(session_factory)

    engine = session_factory.kw["bind"]
    assert engine is not None
    table_names = set(inspect(engine).get_table_names())
    assert "audit_logs" in table_names
    assert "reimbursement_tasks" in table_names
    assert "materials" in table_names


def test_init_database_rejects_unmigrated_schema_when_bootstrap_disabled(tmp_path):
    session_factory = build_session_factory(f"sqlite:///{tmp_path}/production.db")

    with pytest.raises(DatabaseSchemaNotReadyError) as exc_info:
        init_database(session_factory, allow_schema_bootstrap=False)

    assert "alembic upgrade head" in str(exc_info.value)


def test_init_database_accepts_schema_at_alembic_head(tmp_path):
    database_url = f"sqlite:///{tmp_path}/migrated.db"
    alembic_config = build_alembic_config(database_url)
    command.upgrade(alembic_config, "head")

    session_factory = build_session_factory(database_url)

    init_database(session_factory, allow_schema_bootstrap=False)

    assert len(get_alembic_head_revisions()) == 1
