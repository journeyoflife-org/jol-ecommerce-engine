"""Schema provisioning tests — ADR-001 condition 1.

Covers the `migrate_schemas` equivalent: schema creation from the DDL
template, ordered + idempotent migrations across all tenant schemas,
per-tenant failure isolation, and rollback without tenant data corruption.
"""

import uuid
from pathlib import Path

import pytest
from jol_commerce.db.provisioning.schema_provisioner import (
    ProvisioningError,
    Revision,
    SchemaProvisioner,
)
from jol_commerce.tenancy.tenant import Tenant, TenantVertical


def _tenant() -> Tenant:
    return Tenant(
        tenant_id=str(uuid.uuid4()),
        slug=f"t-{uuid.uuid4().hex[:6]}",
        name="Test Tenant",
        vertical=TenantVertical.FAITH_COMMUNITY,
    )


class RecordingExecutor:
    """Records executed SQL; fails on any statement containing `fail_on`."""

    def __init__(self, fail_on: str = "") -> None:
        self.statements: list[str] = []
        self.fail_on = fail_on

    def __call__(self, statement: str) -> None:
        if self.fail_on and self.fail_on in statement:
            raise RuntimeError("simulated database failure")
        self.statements.append(statement)


class TestCreateTenantSchema:
    def test_creates_schema_and_applies_template(self) -> None:
        executor = RecordingExecutor()
        provisioner = SchemaProvisioner(
            template_sql="CREATE TABLE orders(id UUID); CREATE TABLE audit_log(id UUID)",
            executor=executor,
        )
        tenant = _tenant()
        schema = provisioner.create_tenant_schema(tenant)

        assert schema == tenant.schema_name
        assert executor.statements[0] == f"CREATE SCHEMA IF NOT EXISTS {schema}"
        assert "CREATE TABLE orders(id UUID)" in executor.statements
        assert provisioner.pending(schema) == []

    def test_refuses_without_template(self) -> None:
        provisioner = SchemaProvisioner(template_sql="", executor=RecordingExecutor())
        with pytest.raises(ProvisioningError, match="No DDL template"):
            provisioner.create_tenant_schema(_tenant())

    def test_refuses_invalid_tenant_id(self) -> None:
        provisioner = SchemaProvisioner(template_sql="SELECT 1", executor=RecordingExecutor())
        broken = Tenant(
            tenant_id="not-a-uuid",
            slug="broken",
            name="Broken",
            vertical=TenantVertical.FUNERAL_HOME,
        )
        with pytest.raises(ValueError):
            provisioner.create_tenant_schema(broken)


class TestMigrateAll:
    REVISIONS = (
        Revision(
            "001_add_index",
            up_sql="CREATE INDEX idx_a ON orders(x)",
            down_sql="DROP INDEX idx_a",
        ),
        Revision(
            "002_add_col",
            up_sql="ALTER TABLE orders ADD COLUMN y TEXT",
            down_sql="ALTER TABLE orders DROP COLUMN y",
        ),
    )

    def test_applies_pending_revisions_in_order(self) -> None:
        executor = RecordingExecutor()
        tenants = [_tenant(), _tenant()]
        provisioner = SchemaProvisioner(
            template_sql="",
            executor=executor,
            revisions=self.REVISIONS,
        )
        assert provisioner.migrate_all(tenants) == 4  # 2 revisions x 2 tenants

        schema = tenants[0].schema_name
        assert provisioner.pending(schema) == []
        schema_statements = [s for s in executor.statements if schema in s]
        assert schema_statements, "meta insert must be schema-qualified"

    def test_migrate_is_idempotent(self) -> None:
        executor = RecordingExecutor()
        tenants = [_tenant()]
        provisioner = SchemaProvisioner(
            template_sql="",
            executor=executor,
            revisions=self.REVISIONS,
        )
        assert provisioner.migrate_all(tenants) == 2
        assert provisioner.migrate_all(tenants) == 0  # nothing pending on re-run

    def test_failure_in_one_schema_never_corrupts_others(self) -> None:
        healthy, broken = _tenant(), _tenant()
        executor = RecordingExecutor(fail_on=broken.schema_name)
        provisioner = SchemaProvisioner(
            template_sql="",
            executor=executor,
            revisions=self.REVISIONS,
        )
        with pytest.raises(ProvisioningError, match="Provisioning failed"):
            provisioner.migrate_all([healthy, broken])

        assert provisioner.pending(healthy.schema_name) == []  # fully migrated
        assert len(provisioner.pending(broken.schema_name)) == 2  # untouched


class TestDowngrade:
    def test_rolls_back_newest_first_with_explicit_down_artifacts(self) -> None:
        executor = RecordingExecutor()
        tenant = _tenant()
        revisions = (
            Revision(
                "001_add_index",
                up_sql="CREATE INDEX idx_a ON orders(x)",
                down_sql="DROP INDEX idx_a",
            ),
            Revision(
                "002_add_col",
                up_sql="ALTER TABLE orders ADD COLUMN y TEXT",
                down_sql="ALTER TABLE orders DROP COLUMN y",
            ),
        )
        provisioner = SchemaProvisioner(
            template_sql="",
            executor=executor,
            revisions=revisions,
        )
        provisioner.migrate_all([tenant])
        undone = provisioner.downgrade(tenant, "001_add_index")

        assert undone == 1
        downs = [s for s in executor.statements if s.startswith("ALTER TABLE orders DROP")]
        assert len(downs) == 1
        assert provisioner.pending(tenant.schema_name) == ["002_add_col"]

    def test_refuses_rollback_without_down_artifact(self) -> None:
        executor = RecordingExecutor()
        tenant = _tenant()
        revisions = (Revision("001_add_index", up_sql="CREATE INDEX idx_a ON orders(x)"),)
        provisioner = SchemaProvisioner(
            template_sql="",
            executor=executor,
            revisions=revisions,
        )
        provisioner.migrate_all([tenant])
        with pytest.raises(ProvisioningError, match="down artifact"):
            provisioner.downgrade(tenant, "")

    def test_refuses_unknown_target_revision(self) -> None:
        provisioner = SchemaProvisioner(template_sql="", executor=RecordingExecutor())
        with pytest.raises(ProvisioningError, match="not applied"):
            provisioner.downgrade(_tenant(), "999_never_applied")


class TestArtifactsDiscovery:
    def test_pairs_up_and_down_artifacts(self, tmp_path: Path) -> None:
        (tmp_path / "001_init.up.sql").write_text("CREATE TABLE t1(id)", encoding="utf-8")
        (tmp_path / "001_init.down.sql").write_text("DROP TABLE t1", encoding="utf-8")
        (tmp_path / "002_next.up.sql").write_text("CREATE TABLE t2(id)", encoding="utf-8")

        provisioner = SchemaProvisioner.from_artifacts_dir(tmp_path, RecordingExecutor())
        assert [r.revision_id for r in provisioner.revisions] == ["001_init", "002_next"]
        assert provisioner.revisions[0].down_sql == "DROP TABLE t1"
        assert provisioner.revisions[1].down_sql == ""
