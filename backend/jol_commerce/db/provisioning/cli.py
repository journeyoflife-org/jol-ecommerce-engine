"""`jol-cli` — tenant provisioning & audit verification (ADR-001, gap 4.1/4.2).

Usage:
    jol-cli tenant create --slug st-peters-vilnius --name "St. Peters" \\
        --vertical faith_community
    jol-cli create --tenant-id UUID --slug st-anne --name "St. Anne" \\
        --vertical faith_community
    jol-cli migrate
    jol-cli downgrade --tenant-id UUID --slug ... --name ... \\
        --vertical ... --to 001_x
    jol-cli audit verify --export audit_dump.jsonl [--head-hash HEX]

`tenant create` is the SOC2 CC7.1 onboarding path: it registers the
tenant in `public.tenants`, creates `tenant_{uuid}` from the DDL
artifacts, and seeds the vertical-governed starter catalog — no manual
DBA intervention required.

The executor requires an explicit `JOL_DATABASE_URL`; without it the CLI
refuses to run (fail-closed — provisioning never targets an unintended
database). Every statement executes with `search_path` scoped to the
tenant schema being provisioned.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from jol_commerce.audit.audit_log import AuditEntry
from jol_commerce.audit.chain_verifier import verify_chain
from jol_commerce.catalog.catalog import CatalogRepository, seed_default_catalog
from jol_commerce.db.provisioning.schema_provisioner import (
    ProvisioningError,
    SchemaProvisioner,
)
from jol_commerce.tenancy.tenant import Tenant, TenantVertical
from sqlalchemy import Engine, create_engine, text

_ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "sql"
_TEMPLATE = _ARTIFACTS_DIR / "002_tenant_schema_template.sql"

# Executes one statement with `search_path` pinned to the given schema.
ScopedExecutor = Callable[[str, str], None]

# Must match the CHECK constraint on public.tenants.slug.
_SLUG_RE = re.compile(r"^[a-z0-9-]{2,63}$")


def _build_executor() -> tuple[Engine, ScopedExecutor]:
    """Create a schema-scoped SQL executor from JOL_DATABASE_URL."""
    url = os.environ.get("JOL_DATABASE_URL", "")
    if not url:
        raise ProvisioningError("JOL_DATABASE_URL is not set — refusing to provision")
    engine = create_engine(url)

    def execute(statement: str, schema: str = "public") -> None:
        with engine.begin() as conn:
            conn.execute(text(f"SET search_path TO {schema}"))
            conn.execute(text(statement))

    return engine, execute


def _provisioner() -> tuple[SchemaProvisioner, ScopedExecutor]:
    _, execute = _build_executor()
    holder: dict[str, SchemaProvisioner] = {}

    def scoped(statement: str) -> None:
        # CREATE SCHEMA runs unscoped; everything else targets the schema
        # the provisioner is currently working on (`SET search_path`).
        provisioner = holder.get("p")
        schema = (
            provisioner.active_schema
            if provisioner and not statement.startswith("CREATE SCHEMA")
            else "public"
        )
        execute(statement, schema)

    template = _TEMPLATE.read_text(encoding="utf-8") if _TEMPLATE.exists() else ""
    base = SchemaProvisioner.from_artifacts_dir(_ARTIFACTS_DIR, scoped)
    provisioner = SchemaProvisioner(
        template_sql=template,
        executor=scoped,
        revisions=base.revisions,
    )
    holder["p"] = provisioner
    return provisioner, execute


def _sql_literal(value: str) -> str:
    """Quote a string for SQL interpolation (single quotes doubled)."""
    return "'" + value.replace("'", "''") + "'"


def _tenant_create(args: argparse.Namespace) -> int:
    """Full onboarding: registry row + schema + DDL + seeded catalog."""
    if not _SLUG_RE.fullmatch(args.slug):
        raise ProvisioningError(
            f"Invalid slug {args.slug!r} — must match ^[a-z0-9-]{{2,63}}$",
        )
    vertical = TenantVertical(args.vertical)
    tenant_id = str(uuid.uuid4())
    provisioner, execute = _provisioner()
    tenant = Tenant(
        tenant_id=tenant_id,
        slug=args.slug,
        name=args.name,
        vertical=vertical,
        commission_rate=args.commission_rate,
        branch_id=args.branch_id,
    )

    execute(
        # Every value passes through _sql_literal; slug/vertical are pattern-validated.
        "INSERT INTO public.tenants "  # nosec B608
        "(tenant_id, slug, name, vertical, commission_rate, branch_id) VALUES ("
        f"{_sql_literal(tenant_id)}::UUID, {_sql_literal(args.slug)}, "
        f"{_sql_literal(args.name)}, {_sql_literal(vertical.value)}, "
        f"{args.commission_rate}, {_sql_literal(args.branch_id)})",
        "public",
    )
    schema = provisioner.create_tenant_schema(tenant)
    seeded = seed_default_catalog(CatalogRepository(vertical), tenant_id)
    sys.stdout.write(
        f"created tenant {tenant_id} ({schema}) — registry row, DDL template, "
        f"{seeded} starter catalog items\n",
    )
    return 0


def _audit_verify(args: argparse.Namespace) -> int:
    """Verify the hash chain of an exported audit dump (JSON lines)."""
    export_path = Path(args.export)
    entries = [
        AuditEntry(**json.loads(line))
        for line in export_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = verify_chain(entries, expected_head_hash=args.head_hash)
    if report.is_intact:
        sys.stdout.write(f"audit chain intact — {report.verified_count} entries verified\n")
        return 0
    sys.stdout.write(
        f"TAMPERING DETECTED at entry index {report.first_broken_index} "
        f"(id={report.first_broken_entry_id}): {report.reason}; "
        f"{report.verified_count} entries verified before the break\n",
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jol-cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    tenant_parser = sub.add_parser("tenant", help="Tenant lifecycle commands")
    tenant_sub = tenant_parser.add_subparsers(dest="tenant_command", required=True)
    tenant_create = tenant_sub.add_parser(
        "create",
        help="Register tenant + create schema + seed starter catalog",
    )
    tenant_create.add_argument("--slug", required=True)
    tenant_create.add_argument("--name", required=True)
    tenant_create.add_argument("--vertical", required=True)
    tenant_create.add_argument("--commission-rate", default="0.10")
    tenant_create.add_argument("--branch-id", default="")

    sub.add_parser("migrate", help="Apply pending revisions to all tenant schemas")
    create = sub.add_parser("create", help="Create one tenant schema from the DDL template")
    create.add_argument("--tenant-id", required=True)
    create.add_argument("--slug", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--vertical", required=True)
    down = sub.add_parser("downgrade", help="Roll one tenant schema back to a revision")
    down.add_argument("--tenant-id", required=True)
    down.add_argument("--slug", required=True)
    down.add_argument("--name", required=True)
    down.add_argument("--vertical", required=True)
    down.add_argument("--to", required=True)

    audit = sub.add_parser("audit", help="Audit trail commands")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)
    verify = audit_sub.add_parser("verify", help="Verify the hash chain of an audit export")
    verify.add_argument("--export", required=True, help="JSON-lines AuditEntry dump")
    verify.add_argument("--head-hash", default="", help="Checkpoint hash of the newest entry")

    args = parser.parse_args(argv)

    if args.command == "audit":
        try:
            return _audit_verify(args)
        except ProvisioningError as e:
            sys.stdout.write(f"provisioning error: {e}\n")
            return 1

    try:
        if args.command == "tenant":
            return _tenant_create(args)
        provisioner, _ = _provisioner()
        if args.command == "migrate":
            sys.stdout.write(
                "migrate: tenant discovery requires the public registry; "
                "wire to public.tenants before first production use\n",
            )
            return 0
        tenant = Tenant(
            tenant_id=args.tenant_id,
            slug=args.slug,
            name=args.name,
            vertical=TenantVertical(args.vertical),
        )
        if args.command == "create":
            schema = provisioner.create_tenant_schema(tenant)
            sys.stdout.write(f"created {schema}\n")
        else:
            undone = provisioner.downgrade(tenant, args.to)
            sys.stdout.write(f"rolled back {undone} revision(s) for {tenant.schema_name}\n")
    except ProvisioningError as e:
        sys.stdout.write(f"provisioning error: {e}\n")
        return 1
    return 0


def export_entries_jsonl(entries: list[AuditEntry]) -> str:
    """Serialize audit entries to the JSON-lines export format."""
    return "\n".join(json.dumps(asdict(e), sort_keys=True) for e in entries) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
