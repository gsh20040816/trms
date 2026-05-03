from alembic import command
from sqlalchemy import inspect

import pytest

from trms_backend.infrastructure.database import (
    DatabaseSchemaNotReadyError,
    build_alembic_config,
    build_session_factory,
    get_alembic_head_revisions,
    init_database,
)


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

    assert get_alembic_head_revisions() == ("20260503_02",)
