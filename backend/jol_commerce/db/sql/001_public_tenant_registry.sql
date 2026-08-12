-- ============================================================================
-- JOL Commerce Engine — public schema: tenant registry (Blueprint v2.0 §3.4)
--
-- The public schema holds ONLY the tenant registry and shared auth mappings.
-- All business data lives in per-tenant schemas (`tenant_{uuid_hex}`).
-- Access: superuser/migration role only. Application roles must not SELECT
-- this table directly — tenant resolution goes through the registry API.
--
-- Compliance: SOC2 CC6.1 (least privilege), GDPR Art. 30 (registry of
-- processing contexts).
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.tenants (
    tenant_id        UUID PRIMARY KEY,
    slug             TEXT NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{2,63}$'),
    name             TEXT NOT NULL,
    vertical         TEXT NOT NULL CHECK (vertical IN
                       ('faith_community', 'funeral_home', 'cemetery_care')),
    commission_rate  NUMERIC(5, 4) NOT NULL DEFAULT 0.10
                     CHECK (commission_rate >= 0 AND commission_rate <= 1),
    branch_id        TEXT NOT NULL DEFAULT '',
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deactivated_at   TIMESTAMPTZ
);

-- Schema name is derived deterministically: 'tenant_' || replace(tenant_id::text,'-','')
COMMENT ON TABLE public.tenants IS
    'Tenant registry. Public schema contains no business data (Blueprint v2.0 §3.4).';
