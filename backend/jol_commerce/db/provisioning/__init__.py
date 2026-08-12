"""Schema provisioning for tenant schemas (Blueprint v2.0 §3.4, ADR-001).

The FastAPI plane has no `django-tenants migrate_schemas` equivalent, so
schema lifecycle automation lives here: create a tenant schema from the DDL
artifacts, apply pending revisions to every tenant schema, and roll back a
failed migration without corrupting tenant data (ADR-001 condition 1).
"""

from jol_commerce.db.provisioning.schema_provisioner import (
    ProvisioningError,
    SchemaProvisioner,
)

__all__ = ["ProvisioningError", "SchemaProvisioner"]
