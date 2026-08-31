#!/usr/bin/env python3
"""
Add public_id to invoice_clients table in all tenant schemas.
"""
import sys
from pathlib import Path
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import tenant_engine
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_tenant_schemas():
    with tenant_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name LIKE 'tenant_%'
            ORDER BY schema_name
        """))
        return [row[0] for row in result.fetchall()]


def add_public_id(schema_name: str):
    qualified_table = f'"{schema_name}".invoice_clients'
    with tenant_engine.connect() as conn:
        # Check if table exists
        exists = conn.execute(text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema
            AND table_name = 'invoice_clients'
        """), {"schema": schema_name}).fetchone()
        if not exists:
            return

        col_exists = conn.execute(text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = :schema
            AND table_name = 'invoice_clients'
            AND column_name = 'public_id'
        """), {"schema": schema_name}).fetchone()
        if not col_exists:
            conn.execute(text(f'ALTER TABLE {qualified_table} ADD COLUMN public_id VARCHAR(36)'))
            conn.commit()

        # Backfill missing values
        rows = conn.execute(text(f"SELECT id FROM {qualified_table} WHERE public_id IS NULL")).fetchall()
        for row in rows:
            conn.execute(
                text(f"UPDATE {qualified_table} SET public_id = :pid WHERE id = :id"),
                {"pid": str(uuid.uuid4()), "id": row[0]}
            )
        conn.commit()

        # Ensure NOT NULL + unique index
        conn.execute(text(f"ALTER TABLE {qualified_table} ALTER COLUMN public_id SET NOT NULL"))
        conn.execute(text(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS invoice_clients_public_id_idx
            ON {qualified_table} (public_id)
        """))
        conn.commit()


def run():
    schemas = get_tenant_schemas()
    if not schemas:
        logger.info("No tenant schemas found.")
        return

    for schema in schemas:
        try:
            add_public_id(schema)
            logger.info(f"✓ {schema}")
        except Exception as exc:
            logger.error(f"✗ {schema}: {exc}")


if __name__ == "__main__":
    run()
