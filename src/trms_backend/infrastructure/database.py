from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class DatabaseSchemaNotReadyError(RuntimeError):
    pass


def build_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=build_engine(database_url), expire_on_commit=False)


def build_alembic_config(database_url: str | None = None) -> Config:
    root_dir = Path(__file__).resolve().parents[3]
    config = Config(str(root_dir / "alembic.ini"))
    config.set_main_option("script_location", str(root_dir / "alembic"))
    if database_url is not None:
        config.set_main_option("sqlalchemy.url", database_url)
    return config


def get_alembic_head_revisions() -> tuple[str, ...]:
    script_directory = ScriptDirectory.from_config(build_alembic_config())
    return tuple(script_directory.get_heads())


def ensure_database_schema_is_current(session_factory: sessionmaker[Session]) -> None:
    engine = session_factory.kw["bind"]
    assert engine is not None
    inspector = inspect(engine)
    if not inspector.has_table("alembic_version"):
        raise DatabaseSchemaNotReadyError(
            "database schema is not managed by Alembic; run `alembic upgrade head` first"
        )

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_revision = context.get_current_revision()

    head_revisions = get_alembic_head_revisions()
    if current_revision is None:
        raise DatabaseSchemaNotReadyError(
            "database schema has no recorded Alembic revision; run `alembic upgrade head` first"
        )
    if current_revision not in head_revisions:
        expected = ", ".join(head_revisions)
        raise DatabaseSchemaNotReadyError(
            "database schema is not at the expected Alembic head "
            f"(current={current_revision}, expected={expected}); run `alembic upgrade head`"
        )


def init_database(
    session_factory: sessionmaker[Session],
    *,
    allow_schema_bootstrap: bool = True,
) -> None:
    if allow_schema_bootstrap:
        engine = session_factory.kw["bind"]
        assert engine is not None
        Base.metadata.create_all(bind=engine)
        return
    ensure_database_schema_is_current(session_factory)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
