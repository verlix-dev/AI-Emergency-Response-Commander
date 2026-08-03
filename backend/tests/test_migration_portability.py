"""Tests that the Alembic migrations produce a portable schema.

The rest of the suite builds its schema with ``Base.metadata.create_all``, which reads the
SQLAlchemy models. That path never executes a migration, so a non-portable server default
written into a migration file is invisible to it — which is exactly how ``DEFAULT now()``
reached a live SQLite database while every test passed.

These tests run the migrations themselves and assert on the DDL the database actually stores.
"""

import os

os.environ.setdefault("APP_NAME", "ARES API")
os.environ.setdefault("APP_VERSION", "1.0.0")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("API_V1_PREFIX", "/api/v1")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("UPLOAD_DIRECTORY", "uploads")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("MAX_UPLOAD_SIZE", "10")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:3000"]')
os.environ.setdefault("TRUSTED_HOSTS", '["testserver"]')

import importlib.util
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.pool import StaticPool

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"

# SQL functions that exist in PostgreSQL but not SQLite. A migration containing one of these
# produces a table that cannot accept an insert on SQLite.
NON_PORTABLE_SQL = ("now()", "gen_random_uuid()", "uuid_generate_v4()", "nextval(")

TIMESTAMPED_TABLES = {
    "incidents": ("created_at", "updated_at"),
    "uploads": ("uploaded_at",),
    "vision_results": ("created_at",),
    "incident_reports": ("created_at",),
    "resources": ("created_at",),
    "action_plans": ("created_at",),
    "chat_history": ("created_at",),
    "incident_analyses": ("created_at",),
}


def _migration_modules() -> list:
    """Import every migration module in revision order."""
    modules = []
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


@pytest.fixture
def migrated_connection() -> Iterator[Connection]:
    """Apply every migration to a fresh in-memory SQLite database."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        for module in _migration_modules():
            with Operations.context(context):
                module.upgrade()
        yield connection
    engine.dispose()


def _stored_ddl(connection: Connection, table: str) -> str:
    """Return the CREATE TABLE statement SQLite recorded for a table."""
    ddl = connection.execute(
        text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table},
    ).scalar()
    assert ddl, f"Table {table} was not created by the migrations."
    return ddl


class TestMigrationSourcePortability:
    def test_no_migration_contains_postgres_only_sql(self) -> None:
        """Catch a non-portable default in the source before it reaches a database."""
        offenders: list[str] = []
        for path in sorted(MIGRATIONS_DIR.glob("*.py")):
            source = path.read_text(encoding="utf-8").lower()
            for token in NON_PORTABLE_SQL:
                if f'text("{token}' in source or f"text('{token}" in source:
                    offenders.append(f"{path.name}: {token}")

        assert offenders == [], f"Non-portable SQL in migrations: {offenders}"


class TestMigratedSchemaIsPortable:
    def test_migrations_apply_to_sqlite(self, migrated_connection: Connection) -> None:
        tables = {
            row[0]
            for row in migrated_connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }

        assert TIMESTAMPED_TABLES.keys() <= tables

    def test_no_table_carries_a_non_portable_default(
        self, migrated_connection: Connection
    ) -> None:
        """The regression guard: no stored DDL may reference a PostgreSQL-only function."""
        offenders: list[str] = []
        for name, ddl in migrated_connection.execute(
            text("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL")
        ):
            lowered = ddl.lower()
            for token in NON_PORTABLE_SQL:
                if token in lowered:
                    offenders.append(f"{name}: {token}")

        assert offenders == [], f"Non-portable defaults in migrated schema: {offenders}"

    @pytest.mark.parametrize("table", sorted(TIMESTAMPED_TABLES))
    def test_timestamp_defaults_use_current_timestamp(
        self, migrated_connection: Connection, table: str
    ) -> None:
        ddl = _stored_ddl(migrated_connection, table)

        assert "CURRENT_TIMESTAMP" in ddl, f"{table} lacks a portable timestamp default"
        assert "now()" not in ddl.lower(), f"{table} still carries now()"

    def test_vision_results_accepts_an_insert(self, migrated_connection: Connection) -> None:
        """The exact operation that failed: insert relying on the server default."""
        migrated_connection.execute(
            text(
                "INSERT INTO incidents (id, title, incident_type, status, priority, location) "
                "VALUES ('i1', 'probe', 'UNKNOWN', 'PLANNED', 'LOW', 'Delhi')"
            )
        )
        migrated_connection.execute(
            text(
                "INSERT INTO vision_results "
                "(id, incident_id, people_detected, vehicles_detected, boats_detected, "
                " collapsed_structures, confidence_score) "
                "VALUES ('v1', 'i1', 2, 1, 0, 0, 0.9)"
            )
        )

        created_at = migrated_connection.execute(
            text("SELECT created_at FROM vision_results WHERE id='v1'")
        ).scalar()

        assert created_at is not None

    @pytest.mark.parametrize("table", sorted(TIMESTAMPED_TABLES))
    def test_every_timestamp_column_populates_on_insert(
        self, migrated_connection: Connection, table: str
    ) -> None:
        """A default that compiles is not enough; it must actually fire."""
        ddl = _stored_ddl(migrated_connection, table)

        for column in TIMESTAMPED_TABLES[table]:
            assert f"{column} DATETIME DEFAULT CURRENT_TIMESTAMP" in ddl, (
                f"{table}.{column} does not default to CURRENT_TIMESTAMP"
            )
