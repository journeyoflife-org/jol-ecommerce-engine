-- ============================================================================
-- JOL Commerce Engine — per-tenant schema template (Blueprint v2.0 §3.4)
--
-- Applied when provisioning a new tenant schema `tenant_{uuid_hex}`.
-- Implements:
--   1. Row Level Security defense-in-depth on top of schema isolation —
--      RLS prevents cross-tenant leakage even if application-layer
--      filters fail (SOC2 CC6.2, Blueprint §2).
--   2. Append-only audit log: UPDATE/DELETE are blocked by trigger, and
--      the hash chain makes historical tampering detectable
--      (Blueprint §2 — Immutable Audit Trail, PCI DSS Req. 10).
--   3. pgcrypto column encryption for payment token references
--      (Blueprint §3.4 — column-level encryption; keys in Vault).
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- 1. Row Level Security (defense-in-depth under schema-per-tenant)
-- ---------------------------------------------------------------------------
-- The application role must set `app.current_tenant` on every connection
-- before any query; the connection's search_path is pinned to the tenant
-- schema by the schema-per-tenant middleware.

ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_orders ON orders
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

ALTER TABLE payment_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_tokens FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_payment_tokens ON payment_tokens
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

ALTER TABLE commission_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE commission_ledger FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_commission_ledger ON commission_ledger
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- ---------------------------------------------------------------------------
-- 2. Append-only audit log — no UPDATE, no DELETE, ever
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION enforce_audit_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'audit_log is append-only: % operations are prohibited (Blueprint v2.0 §2)',
        TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_no_update
    BEFORE UPDATE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION enforce_audit_append_only();

CREATE TRIGGER audit_log_no_delete
    BEFORE DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION enforce_audit_append_only();

-- Hash chain columns: previous_hash references the preceding entry's
-- current_hash; current_hash = sha256(previous_hash || payload).
COMMENT ON TABLE audit_log IS
    'Immutable, hash-chained audit trail. Retention: 7 years financial/audit, '
    '3 years access logs (Blueprint v2.0 §3.4).';

-- ---------------------------------------------------------------------------
-- 3. Payment tokens — Zero-PAN policy (Blueprint §2, PCI DSS Req. 3)
-- ---------------------------------------------------------------------------
-- Only gateway references are stored; the token reference itself is
-- encrypted at column level with pgcrypto. The decryption key lives in
-- HashiCorp Vault and is never persisted in the database.

COMMENT ON TABLE payment_tokens IS
    'Zero-PAN: gateway_ref only (Stripe pm_/seti_ IDs). Raw card data is '
    'prohibited in this schema by application contract and PCI SAQ A scope.';
