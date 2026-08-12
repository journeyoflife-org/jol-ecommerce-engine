"""RLS defense-in-depth contract tests — Blueprint §3.4, ADR-001.

The application-layer tenant guards (CrossTenantAccessError) are verified
elsewhere; these tests verify the *database-layer* safety net by
asserting the DDL artifacts enforce RLS for every tenant-owned table.
They run without a live database so CI can never ship a template that
silently drops the policies; a live RLS leak test belongs in the
penetration test scope (`docs/penetration-test-scope.md`).
"""

from pathlib import Path

import jol_commerce

_TEMPLATE = Path(jol_commerce.__file__).parent / "db" / "sql" / "002_tenant_schema_template.sql"

# Every table that stores tenant data must carry RLS (Blueprint §3.4).
TENANT_TABLES = ("orders", "payment_tokens", "commission_ledger")


class TestRlsPolicies:
    def _ddl(self) -> str:
        return _TEMPLATE.read_text(encoding="utf-8")

    def test_every_tenant_table_enables_and_forces_rls(self) -> None:
        ddl = self._ddl()
        for table in TENANT_TABLES:
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in ddl, table
            # FORCE applies the policy to the table owner too — without it
            # a superuser/owner connection bypasses isolation entirely.
            assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in ddl, table

    def test_every_policy_binds_to_the_request_tenant_setting(self) -> None:
        ddl = self._ddl()
        for table in TENANT_TABLES:
            assert f"tenant_isolation_{table}" in ddl, table
        # The policy predicate must compare against the session setting the
        # middleware/migrations set per request — never a literal.
        assert ddl.count("current_setting('app.current_tenant')") >= len(TENANT_TABLES)


class TestAppendOnlyAudit:
    def test_audit_trigger_blocks_update_and_delete(self) -> None:
        ddl = _TEMPLATE.read_text(encoding="utf-8")
        assert "enforce_audit_append_only" in ddl
        assert "UPDATE" in ddl and "DELETE" in ddl
        assert "BEFORE UPDATE ON audit_log" in ddl
        assert "BEFORE DELETE ON audit_log" in ddl
        assert "audit_log" in ddl
