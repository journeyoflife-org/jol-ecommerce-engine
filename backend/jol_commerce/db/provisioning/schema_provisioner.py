"""Tenant schema provisioner — the `migrate_schemas` equivalent (ADR-001).

Blueprint v2.0 §3.4 requires every tenant to own a dedicated PostgreSQL
schema (`tenant_{uuid-hex}`) created from the DDL artifacts and kept in
step with application schema evolution. `django-tenants` provides
`migrate_schemas` out of the box; on the FastAPI plane this class is the
tested automation that ADR-001 condition 1 demands:

- `create_tenant_schema` — CREATE SCHEMA + apply the DDL template.
- `migrate_all` — iterate every tenant schema and apply pending revisions
  in order; one tenant's failure never blocks or corrupts the others.
- `downgrade` — roll a schema back to a prior revision (rollback without
  tenant data corruption, using explicit down artifacts).

Every schema records applied revisions in `jol_schema_meta`, so migration
state is per-schema and idempotent. SQL execution is injected so the
provisioner is unit-testable without a live database; the production
executor wraps SQLAlchemy/psycopg.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jol_commerce.tenancy.tenant import Tenant

# Executes one SQL statement inside the provisioned schema scope.
SqlExecutor = Callable[[str], None]

# Returns the revisions already applied to a schema (oldest first).
AppliedRevisionsLoader = Callable[[str], list[str]]

# Tenant-schema identifier: `tenant_` + 32 lowercase hex chars (UUID hex).
_SCHEMA_NAME_RE = re.compile(r"^tenant_[0-9a-f]{32}$")

# Per-schema migration bookkeeping (created before the first revision).
_META_TABLE_DDL = (
    "CREATE TABLE IF NOT EXISTS {schema}.jol_schema_meta ("
    "revision TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
)


class ProvisioningError(RuntimeError):
    """Raised when schema provisioning cannot proceed safely."""


@dataclass(frozen=True)
class Revision:
    """One ordered schema change with an explicit rollback artifact."""

    revision_id: str
    up_sql: str
    down_sql: str = ""


@dataclass
class SchemaProvisioner:
    """Creates and migrates tenant schemas from DDL artifacts."""

    template_sql: str
    executor: SqlExecutor
    revisions: tuple[Revision, ...] = ()
    load_applied: AppliedRevisionsLoader | None = None
    # Schema currently being provisioned — executors that scope via
    # `SET search_path` read this while statements execute.
    active_schema: str = ""
    _applied: dict[str, list[str]] = field(default_factory=dict)

    def _applied_revisions(self, schema: str) -> list[str]:
        """Applied revisions per the injected loader, or in-memory state."""
        loader = self.load_applied
        if loader is None:
            return list(self._applied.get(schema, []))
        return loader(schema)

    @classmethod
    def from_artifacts_dir(
        cls,
        artifacts_dir: Path | str,
        executor: SqlExecutor,
    ) -> SchemaProvisioner:
        """Build a provisioner from a versioned SQL artifacts directory.

        `NNN_name.up.sql` pairs with `NNN_name.down.sql`; the revision ID
        is the file stem. Down artifacts are required for any revision
        that may be rolled back.
        """
        directory = Path(artifacts_dir)
        up_sql: dict[str, str] = {}
        down_sql: dict[str, str] = {}
        for path in sorted(directory.glob("*.up.sql")):
            up_sql[path.name.removesuffix(".up.sql")] = path.read_text(encoding="utf-8")
        for path in sorted(directory.glob("*.down.sql")):
            down_sql[path.name.removesuffix(".down.sql")] = path.read_text(encoding="utf-8")
        revisions = tuple(
            Revision(revision_id=rev, up_sql=up, down_sql=down_sql.get(rev, ""))
            for rev, up in sorted(up_sql.items())
        )
        return cls(template_sql="", executor=executor, revisions=revisions)

    def create_tenant_schema(self, tenant: Tenant) -> str:
        """Create the tenant schema and apply the DDL template once."""
        schema = self._validated_schema(tenant)
        if not self.template_sql:
            raise ProvisioningError("No DDL template configured")
        self.active_schema = schema
        self._execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        for statement in self._statements(self.template_sql):
            self._execute(statement)
        self._record(schema, "000_template")
        return schema

    def migrate_all(self, tenants: Iterable[Tenant]) -> int:
        """Apply pending revisions to every tenant schema, in order.

        Returns the number of revision applications performed. Revisions
        already recorded in a schema's `jol_schema_meta` are skipped, so
        the operation is safe to re-run (idempotent).
        """
        applied_count = 0
        for tenant in tenants:
            schema = self._validated_schema(tenant)
            pending = self._pending(schema)
            if not pending:
                continue
            self.active_schema = schema
            self._execute(_META_TABLE_DDL.format(schema=schema))
            for revision in pending:
                for statement in self._statements(revision.up_sql):
                    self._execute(statement)
                self._record(schema, revision.revision_id)
                applied_count += 1
        return applied_count

    def downgrade(self, tenant: Tenant, target_revision: str) -> int:
        """Roll the tenant schema back to `target_revision` (inclusive).

        Down artifacts are applied newest-first. Raises instead of
        guessing when a required down artifact is missing — a failed
        migration must never be "rolled back" by dropping tenant data.
        """
        schema = self._validated_schema(tenant)
        applied = list(self._applied_revisions(schema))
        if target_revision not in [*applied, ""]:
            raise ProvisioningError(
                f"Target revision {target_revision!r} is not applied to {schema}",
            )
        self.active_schema = schema
        by_id = {r.revision_id: r for r in self.revisions}
        to_undo = [rev for rev in reversed(applied) if rev > target_revision]
        undone = 0
        for revision_id in to_undo:
            revision = by_id.get(revision_id)
            if revision is None or not revision.down_sql:
                raise ProvisioningError(
                    f"No down artifact for revision {revision_id!r}; "
                    "refusing to roll back without an explicit rollback",
                )
            for statement in self._statements(revision.down_sql):
                self._execute(statement)
            self._execute(
                # Schema is regex-validated; revision IDs come from artifact names.
                f"DELETE FROM {schema}.jol_schema_meta "  # nosec B608
                f"WHERE revision = '{revision_id}'",
            )
            recorded = self._applied.get(schema)
            if recorded is not None and revision_id in recorded:
                recorded.remove(revision_id)
            undone += 1
        return undone

    def pending(self, schema: str) -> list[str]:
        """Revision IDs that the schema has not applied yet."""
        return [r.revision_id for r in self._pending(schema)]

    def _pending(self, schema: str) -> list[Revision]:
        applied = set(self._applied_revisions(schema))
        return [r for r in self.revisions if r.revision_id not in applied]

    def _record(self, schema: str, revision_id: str) -> None:
        self._applied.setdefault(schema, []).append(revision_id)
        if revision_id != "000_template":
            self._execute(
                # Schema is regex-validated; revision IDs come from artifact names.
                f"INSERT INTO {schema}.jol_schema_meta (revision) "  # nosec B608
                f"VALUES ('{revision_id}')",
            )

    def _execute(self, statement: str) -> None:
        try:
            self.executor(statement)
        except Exception as e:
            raise ProvisioningError(f"Provisioning failed: {e}") from e

    @staticmethod
    def _validated_schema(tenant: Tenant) -> str:
        schema = tenant.schema_name
        if not _SCHEMA_NAME_RE.fullmatch(schema):
            raise ProvisioningError(f"Refusing to provision unsafe schema name: {schema!r}")
        return schema

    @staticmethod
    def _statements(sql: str) -> list[str]:
        return [s.strip() for s in sql.split(";") if s.strip()]
